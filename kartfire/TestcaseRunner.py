#	kartfire - Test framework to consistently run submission files
#	Copyright (C) 2023-2025 Johannes Bauer
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
from .Enums import TestresultStatus
#from .Exceptions import InternalError
#from .SubmissionEvaluation import SubmissionEvaluation
#from .Docker import Docker

_log = logging.getLogger(__spec__.name)

class TestcaseRunner():
	def __init__(self, testcase_collection: "TestcaseCollection", test_fixture_config: "TestFixtureConfig", database: "Database"):
		self._testcases = testcase_collection
		self._config = test_fixture_config
		self._db = database
		_log.debug("Successfully started testcase runner with %d testcases", len(self._testcases))
		self._concurrent_process_count = self._determine_concurrent_process_count()
		self._process_semaphore = None

	@property
	def testcases(self):
		return self._testcases

	@property
	def config(self):
		return self._config

	@functools.cached_property
	def total_maximum_runtime_secs(self):
		timeout = 30
		timeout += self._config.max_setup_time_secs
		timeout += sum(testcase.reference_runtime_secs or 0 for testcase in self._testcases)
		timeout = round(timeout)
		return timeout

	@functools.cached_property
	def container_environment(self):
		docker = Docker(self._config.docker_executable)
		container_info = docker.inspect_image(self._config.docker_container)
		return {
			"image_name": self._config.docker_container,
			"labels": container_info.get("Config", { }).get("Labels", { })
		}

	@functools.cached_property
	def guest_testcase_data(self):
		"""This is the test data that ends up directly inside the runner. It
		may not contain the correct answers. Automatically groups collections
		in own batches and packs up to testbatch_maxsize testcases into each
		batch."""
		testbatch = [ ]
		for collection in self._testcase_collections:
			testbatch += [ testcase.guest_data for testcase in collection ]
		return testbatch

	@functools.cached_property
	def required_server_containers(self):
		"""Determine all server containers that are required to test the
		submission."""
		requirements = { }
		for collection in self._testcase_collections:
			for (requirement_name, requirement_data) in collection.requirements.items():
				if requirement_name in requirements:
					if requirement_data != requirements[requirement_name]:
						raise ValueError("Same network alias used for incompatible image configurations: {requirement_data} and {requirements[requirement_name]}")
				else:
					requirements[requirement_name] = requirement_data
		return requirements

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

	def _evaluate_run_result(self, runid: int, submission_run_result: "SubmissionRunResult"):
		for stdout_line in submission_run_result.stdout.decode("utf-8", errors = "ignore").split("\n"):
			try:
				json_data = json.loads(stdout_line)
				if not isinstance(json_data, dict):
					continue
				if "id" not in json_data:
					continue
				if "reply" not in json_data:
					continue
				if not json_data["id"].isdigit():
					continue
				tcid = int(json_data["id"])
				if tcid not in self._testcases:
					print(f"Submission returned TCID {tcid} which is not not in testcase battery")
					continue
				testcase = self._testcases[tcid]

				if testcase.correct_response is None:
					# No response available
					test_result_status = TestresultStatus.Indeterminate
				elif testcase.correct_response == json_data["reply"]:
					test_result_status = TestresultStatus.Pass
				else:
					test_result_status = TestresultStatus.Fail

				self._db.insert_run_result(runid, tcid, json_data["reply"], test_result_status)
				self._db.opportunistic_commit()
			except json.decoder.JSONDecodeError:
				pass
		self._db.commit()

	async def _run_submission(self, submission: "Submission"):
		async with self._process_semaphore:
			_log.info("Starting testing of submission \"%s\"", submission)
			runid = self._db.create_testrun()
			self._db.commit()
			submission_run_result = await submission.run(self, interactive = self._config.interactive)
			self._evaluate_run_result(runid, submission_run_result)
			self._db.commit()

	async def _run(self, submissions: list["Submission"]):
		self._process_semaphore = asyncio.Semaphore(self._concurrent_process_count)

		batch_count = (len(submissions) + self._concurrent_process_count - 1) // self._concurrent_process_count
		wctime_mins = round((self.total_maximum_runtime_secs * batch_count) / 60)
		_log.debug("Now testing %d submission(s) against %d testcases, maximum runtime per submission is %d:%02d minutes:seconds; worst case total runtime is %d:%02d hours:minutes", len(submissions), len(self._testcases), self.total_maximum_runtime_secs // 60, self.total_maximum_runtime_secs % 60, wctime_mins // 60, wctime_mins % 60)
		async with asyncio.TaskGroup() as task_group:
			for submission in submissions:
				task_group.create_task(self._run_submission(submission))

	def run(self, submissions: list["Submission"]):
		return asyncio.run(self._run(submissions))
