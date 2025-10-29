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

import os
import tempfile
import asyncio
import logging
import json
import time
import dataclasses
from .Tools import SystemTools
from .Enums import TestrunStatus, TestresultStatus
from .Exceptions import InternalError
from .Docker import Docker

_log = logging.getLogger(__spec__.name)

@dataclasses.dataclass
class SubmissionRunResult():
	submission: "Submission"
	stdout: bytes
	stderr: bytes
	testrun_status: TestrunStatus
	error_details: dict | None = None
	runtime_secs: float | None = None

@dataclasses.dataclass
class RunConstraints():
	max_permissible_runtime_secs: float | None
	max_permissible_ram_mib: int

class TestRunner():
	def __init__(self, testcase_collections: list["TestcaseCollection"], test_fixture_config: "TestFixtureConfig", database: "Database", interactive: bool = False):
		self._testcase_collections = testcase_collections
		self._config = test_fixture_config
		self._db = database
		self._interactive = interactive
		_log.debug("Successfully started testcase runner with %d collections and %s total testcases", len(self._testcase_collections), sum(len(collection) for collection in self._testcase_collections))
		self._concurrent_process_count = self._determine_concurrent_process_count()
		self._process_semaphore = None
		self._submission_run_finished_callbacks = [ ]
		self._submission_all_runs_finished_callbacks = [ ]

	def register_run_finished_callback(self, callback: callable):
		self._submission_run_finished_callbacks.append(callback)

	def register_all_runs_finished_callback(self, callback: callable):
		self._submission_all_runs_finished_callbacks.append(callback)

	@property
	def config(self):
		return self._config

	@property
	def container_testrunner_filename(self):
		return os.path.realpath(os.path.dirname(__file__)) + "/container/container_testrunner"

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

	def _evaluate_run_result(self, run_id: int, collection: "TestcaseCollection", submission_run_result: "SubmissionRunResult"):
		for stdout_line in submission_run_result.stdout.decode("utf-8", errors = "ignore").split("\n"):
			try:
				json_data = json.loads(stdout_line)
				if not isinstance(json_data, dict):
					continue

				if ("_" in json_data) and (json_data["_"] == "9d83e7a5-bb94-40a1-9f59-a6586d2c3c94"):
					# Exception in subordinate process
					if json_data.get("code", "N/A") in [ "exec_timeout", "exec_oom" ]:
						submission_run_result.testrun_status = TestrunStatus.Terminated
					else:
						submission_run_result.testrun_status = TestrunStatus.Failed
					submission_run_result.error_details = json_data.get("exception")

				if "id" not in json_data:
					continue
				if "reply" not in json_data:
					continue
				if not json_data["id"].isdigit():
					continue
				tc_id = int(json_data["id"])
				if tc_id not in collection:
					print(f"Submission returned TCID {tc_id} which is not not in testcase battery")
					continue
				testcase = collection[tc_id]

				if testcase.correct_reply is None:
					# No response available
					test_result_status = TestresultStatus.Indeterminate
				elif testcase.correct_reply == json_data["reply"]:
					test_result_status = TestresultStatus.Pass
				else:
					test_result_status = TestresultStatus.Fail

				self._db.update_testresult(run_id, tc_id, json_data["reply"], test_result_status)
				self._db.opportunistic_commit()
			except json.decoder.JSONDecodeError:
				pass
		self._db.close_testrun(run_id, submission_run_result)
		self._db.commit()

	def _determine_max_permissible_runtime_secs(self, collection: "TestcaseCollection"):
		if (collection.reference_runtime_secs is None) or (self._config.reference_time_factor is None):
			# Infinity, never timeout solutions (this should only be done for
			# known good solutions to gauge the reference time)
			return None
		else:
			return self._config.minimum_testbatch_time_secs + self._config.max_setup_time_secs + (collection.reference_runtime_secs * self._config.reference_time_factor)

	async def _run_submission_collection(self, submission: "Submission", collection: "TestcaseCollection"):
		container_meta = {
			"container_dut_dir":				"/dut",
			"container_submission_tar_file":	"/dut.tar",
			"container_testcase_file":			"/testcases.json",

			"setup_name":						self._config.setup_name,
			"max_setup_time_secs":				self._config.max_setup_time_secs,
			"solution_name":					self._config.solution_name,
			"max_runtime_secs":					self._determine_max_permissible_runtime_secs(collection),

			"verbose":							2 if self._interactive else 0,
		}
		container_testcases = {
			"testcases": { str(testcase.tc_id): testcase.guest_dict() for testcase in collection },
		}

		original_container_command = [ "/container_testrunner" ]
		container_command = original_container_command
		if self._interactive:
			print(f"Trigger test runner using: {' '.join(container_command)}")
			container_command = [ "/bin/bash" ]

		_log.debug(f"Creating docker container to run submission \"%s\", time allowance is {'infinite' if (container_meta['max_runtime_secs'] is None) else f'{container_meta['max_runtime_secs']:.1f} secs'}", str(submission))

		async with Docker(docker_executable = self._config.docker_executable) as docker:
			network = await docker.create_network()

			# Start all dependent servers (e.g., a server container that the
			# submission needs to connect to)
			for (server_alias, server_config) in collection.dependencies.items():
				_log.debug("Starting dependent server %s with config %s.", server_alias, str(server_config))
				server_container = await docker.create_container(docker_image_name = server_config["image"], command = server_config["command"], network = network, network_alias = server_alias, run_name_prefix = f"kartfire_hlp_{submission.shortname}_{server_alias}")
				await server_container.start()

			container = await docker.create_container(docker_image_name = self._config.docker_container, command = container_command, network = network, max_memory_mib = self._config.max_memory_mib, interactive = self._interactive, run_name_prefix = f"kartfire_run_{submission.shortname}")
			await container.cp(self.container_testrunner_filename, "/container_testrunner")
			with tempfile.NamedTemporaryFile(suffix = ".tar") as tmp:
				await submission.create_submission_tarfile(tmp.name)
				await container.cp(tmp.name, container_meta["container_submission_tar_file"])
			await container.write_json(container_meta, "/meta.json", pretty_print = self._interactive)
			await container.write_json(container_testcases, container_meta["container_testcase_file"], pretty_print = self._interactive)
			if self._interactive:
				await container.cpdata(f"{' '.join(original_container_command)}\n".encode("utf-8"), "/root/.bash_history")
			await container.start()
			if self._interactive:
				await container.attach()

			t0 = time.time()
			finished = await container.wait_timeout(container_meta["max_runtime_secs"])
			runtime_secs = time.time() - t0
			if finished is None:
				# Docker container time timed out
				_log.debug("Docker container with submission \"%s\" timed out after %d seconds", str(submission), container_meta["max_runtime_secs"])
				testrun_status = TestrunStatus.Terminated
			elif finished == 0:
				_log.debug("Docker container with submission \"%s\" exited normally.", str(submission))
				testrun_status = TestrunStatus.Finished
			else:
				_log.debug("Docker container with submission \"%s\" exited with status code %d.", str(submission), finished)
				testrun_status = TestrunStatus.Failed

			(stdout, stderr) = await container.logs()
			return SubmissionRunResult(submission = submission, stdout = stdout, stderr = stderr, testrun_status = testrun_status, runtime_secs = runtime_secs)

	async def _run_submission(self, submission: "Submission"):
		async with self._process_semaphore:
			_log.info("Starting testing of submission \"%s\"", submission)
			run_ids = [ ]
			for collection in self._testcase_collections:
				run_id = self._db.create_testrun(submission, collection, run_constraints = RunConstraints(max_permissible_runtime_secs = self._determine_max_permissible_runtime_secs(collection), max_permissible_ram_mib = self._config.max_memory_mib))
				run_ids.append(run_id)
				self._db.commit()
				submission_run_result = await self._run_submission_collection(submission, collection)
				self._evaluate_run_result(run_id, collection, submission_run_result)
				self._db.commit()
				for callback in self._submission_run_finished_callbacks:
					callback(submission, run_id)
			for callback in self._submission_all_runs_finished_callbacks:
				callback(submission, run_ids)

	async def _run(self, submissions: list["Submission"]):
		self._process_semaphore = asyncio.Semaphore(self._concurrent_process_count)
		_log.debug("Now testing %d submission(s) against %d collections", len(submissions), len(self._testcase_collections))
		async with asyncio.TaskGroup() as task_group:
			for submission in submissions:
				task_group.create_task(self._run_submission(submission))

	def run(self, submissions: list["Submission"]):
		return asyncio.run(self._run(submissions))
