#	kartfire - Test framework to consistently run submission files
#	Copyright (C) 2023-2024 Johannes Bauer
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
from .SubmissionEvaluation import SubmissionEvaluation

_log = logging.getLogger(__spec__.name)

class TestcaseRunner():
	def __init__(self, testcase_collections: list["TestcaseCollection"], test_fixture_config: "TestFixtureConfig"):
		self._testcase_collections = testcase_collections
		self._testcases_by_name = self._get_all_testcases_by_name()
		self._test_fixture_config = test_fixture_config
		_log.debug("Successfully loaded %d testcase collection(s)", len(self._testcase_collections))
		self._config = test_fixture_config
		self._concurrent_process_count = self._determine_concurrent_process_count()
		self._process_semaphore = None
		asyncio.Semaphore(self._concurrent_process_count)

	def _get_all_testcases_by_name(self) -> dict[str, "Testcase"]:
		testcase_names = { }
		for testcase_collection in self._testcase_collections:
			collection_names = testcase_collection.testcases_by_name
			if len(set(testcase_names) & set(collection_names)) > 0:
				raise InternalError("Duplicate test case names (same name in multiple collections).")
			testcase_names.update(collection_names)
		return testcase_names

	@property
	def config(self):
		return self._config

	@functools.cached_property
	def actions(self):
		return set(testcase.action for testcase in self)

	@functools.cached_property
	def testcase_count(self):
		return sum(testcase_collection.testcase_count for testcase_collection in self._testcase_collections)

	@functools.cached_property
	def total_maximum_runtime_secs(self):
		timeout = 30
		timeout += self._config.max_setup_time_secs
		timeout += sum(testcase.runtime_allowance_secs for testcase in self)
		timeout = round(timeout)
		return timeout

	@functools.cached_property
	def guest_testbatch_data(self):
		"""This is the test data that ends up directly inside the runner. It
		may not contain the correct answers. Automatically groups collections
		in own batches and packs up to testbatch_maxsize testcases into each
		batch."""
		testbatch = [ ]
		for collection in self._testcase_collections:
			for batch in collection.get_batched(self._config.testbatch_maxsize):
				testbatch.append([ testcase.guest_data for testcase in batch ])
		return testbatch

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
		async with self._process_semaphore:
			_log.info("Starting testing of submission %s", submission)
			testrunner_output = await submission.run(self, interactive = self._test_fixture_config.interactive)
			submission_evaluation = SubmissionEvaluation(testrunner_output, self, submission)
		return submission_evaluation

	async def _run(self, submissions: list["Submission"]):
		self._process_semaphore = asyncio.Semaphore(self._concurrent_process_count)

		batch_count = (len(submissions) + self._concurrent_process_count - 1) // self._concurrent_process_count
		wctime_mins = round((self.total_maximum_runtime_secs * batch_count) / 60)
		_log.debug("Now testing %d submission(s) against %d testcases, maximum runtime per submission is %d:%02d minutes:seconds; worst case total runtime is %d:%02d hours:minutes", len(submissions), self.testcase_count, self.total_maximum_runtime_secs // 60, self.total_maximum_runtime_secs % 60, wctime_mins // 60, wctime_mins % 60)
		tasks = [ ]
		for submission in submissions:
			task = asyncio.create_task(self._run_submission(submission))
			tasks.append(task)
		submission_evaluations = await asyncio.gather(*tasks)
		return submission_evaluations

	def run(self, submissions: list["Submission"]):
		return asyncio.run(self._run(submissions))

	def __getitem__(self, testcase_name: str) -> "Testcase":
		return self._testcases_by_name[testcase_name]

	def __iter__(self):
		for testcase_collection in self._testcase_collections:
			yield from iter(testcase_collection)
