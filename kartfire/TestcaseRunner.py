#	kartfire - Test framework to consistently run submission files
#	Copyright (C) 2023-2023 Johannes Bauer
#
#	This file is part of kartfire.
#
#	kartfire is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	kartfire is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with kartfire; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>

import asyncio
import logging
import functools
import json
from .Tools import SystemTools
from .Exceptions import InternalError

_log = logging.getLogger(__spec__.name)

class TestcaseRunner():
	def __init__(self, testcase_collections: list["TestcaseCollection"], test_fixture_config: "TestFixtureConfig"):
		self._testcase_collections = testcase_collections
		_log.debug("Successfully loaded %d testcase collection(s)", len(self._testcase_collections))
		self._config = test_fixture_config
		self._concurrent_process_count = self._determine_concurrent_process_count()
		self._process_semaphore = asyncio.Semaphore(self._concurrent_process_count)

	@property
	def config(self):
		return self._config

	@functools.cached_property
	def testcase_count(self):
		return sum(testcase_collection.testcase_count for testcase_collection in self._testcase_collections)

	@functools.cached_property
	def total_maximum_runtime_secs(self):
		timeout = 30
		timeout += self._config.max_build_time_secs
		timeout += sum(testcase.runtime_allowance_secs for testcase in self)
		return timeout

	@functools.cached_property
	def client_testcase_data(self):
		client_testcases = [ testcase.client_data for testcase in self ]
		return json.dumps(client_testcases).encode("ascii")

	def _determine_concurrent_process_count(self):
		host_memory_mib = SystemTools.get_host_memory_mib()
		usable_ram = round(host_memory_mib * (self._config.host_memory_usage_percent / 100))
		concurrent_by_ram = usable_ram // self._config.max_memory_mib
		concurrent_by_proc = self._config.max_concurrent_processes
		concurrent = min(concurrent_by_ram, concurrent_by_proc)
		_log.debug("Host memory is %d MiB, usable memory is %.0f%% of that -> %d MiB; %d MiB per testcase runner limits to %d processes by RAM. %d max processes allowed -> %d final total process count", host_memory_mib, self._config.host_memory_usage_percent, usable_ram, self._config.max_memory_mib, concurrent_by_ram, concurrent_by_proc, concurrent)
		if concurrent < 1:
			raise InternalError("Limitations on RAM/process count allow running of no process at all.")
		return concurrent

	async def _run_submission(self, submission: "Submission"):
		await submission.run(self)

	async def _run(self, submissions: list["Submission"]):
		_log.debug("Now testing %d submission(s)", len(submissions))
		tasks = [ ]
		for submission in submissions:
			task = asyncio.create_task(self._run_submission(submission))
			tasks.append(task)
		await asyncio.gather(*tasks)

	def run(self, submissions: list["Submission"]):
		asyncio.run(self._run(submissions))

	def __iter__(self):
		for testcase_collection in self._testcase_collections:
			yield from iter(testcase_collection)
