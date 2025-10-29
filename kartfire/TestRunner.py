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
class ExecutionResult():
	stdout: bytes
	stderr: bytes
	testrun_status: TestrunStatus
	error_details: dict | None = None
	runtime_secs: float | None = None
	pre_run_result: "any | None" = None
	post_run_result: "any | None" = None

@dataclasses.dataclass
class BuildConstraints():
	runtime_allowance_secs: float | None

@dataclasses.dataclass
class RunConstraints():
	runtime_allowance_secs: float | None
	max_permissible_ram_mib: int

@dataclasses.dataclass
class ContainerImageMetadata():
	name: str
	source: str
	revision: str
	created: str

	@classmethod
	def collect(cls, image_name: str, docker: Docker):
		data = docker.inspect_image(image_name)
		labels = data.get("Config", { }).get("Labels", { })
		return cls(name = image_name, source = labels.get("org.opencontainers.image.source"), revision = labels.get("org.opencontainers.image.revision"), created = labels.get("org.opencontainers.image.created"))

	def to_dict(self):
		return dataclasses.asdict(self)

class TestRunner():
	_DEFS = {
		"container_testrunner":				"/container_testrunner",
		"container_dut_dir":				"/dut",
		"container_submission_tar_file":	"/dut.tar",
		"container_testcase_file":			"/testcases.json",
		"container_meta_file":				"/meta.json",
	}

	def __init__(self, testcase_collections: list["TestcaseCollection"], test_fixture_config: "TestFixtureConfig", database: "Database", interactive: bool = False):
		self._testcase_collections = testcase_collections
		self._config = test_fixture_config
		self._db = database
		self._interactive = interactive
		_log.debug("Successfully started testcase runner with %d collections and %s total testcases", len(self._testcase_collections), sum(len(collection) for collection in self._testcase_collections))
		self._concurrent_process_count = self._determine_concurrent_process_count()
		self._process_semaphore = None
		self._submission_build_finished_callbacks = [ ]
		self._submission_run_finished_callbacks = [ ]
		self._submission_multirun_finished_callbacks = [ ]

	def register_build_finished_callback(self, callback: callable):
		self._submission_build_finished_callbacks.append(callback)

	def register_run_finished_callback(self, callback: callable):
		self._submission_run_finished_callbacks.append(callback)

	def register_multirun_finished_callback(self, callback: callable):
		self._submission_multirun_finished_callbacks.append(callback)

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

	def _evaluate_docker_stdout(self, exec_result: "ExecutionResult", run_id: int = None, collection: "TestcaseCollection | None" = None):
		for stdout_line in exec_result.stdout.decode("utf-8", errors = "ignore").split("\n"):
			try:
				json_data = json.loads(stdout_line)
				if not isinstance(json_data, dict):
					continue

				if ("_" in json_data) and (json_data["_"] == "9d83e7a5-bb94-40a1-9f59-a6586d2c3c94"):
					# Exception in subordinate process
					if json_data.get("code", "N/A") in [ "exec_timeout", "exec_oom" ]:
						exec_result.testrun_status = TestrunStatus.Terminated
					else:
						exec_result.testrun_status = TestrunStatus.Failed
					exec_result.error_details = json_data.get("exception")

				if run_id is not None:
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
		if run_id is not None:
			self._db.close_testrun(run_id, exec_result)
			self._db.commit()

	def _determine_runtime_allowance_secs(self, collection: "TestcaseCollection"):
		if (collection.reference_runtime_secs is None) or (self._config.reference_time_factor is None):
			# Infinity, never timeout solutions (this should only be done for
			# known good solutions to gauge the reference time)
			return None
		else:
			return self._config.minimum_testbatch_time_secs + (collection.reference_runtime_secs * self._config.reference_time_factor)

	@property
	def docker(self):
		return Docker(docker_executable = self._config.docker_executable)

	async def _initialize_docker_env(self, docker: Docker):
		await docker.create_network()

	async def _execute_docker_container_run(self, docker: Docker, image_name: str, container_command: list[str], prefix: str, pre_run_hook: "callable | None" = None, post_run_hook: "callable | None" = None, timeout_secs: float | None = None) -> ExecutionResult:
		(pre_run_result, post_run_result) = (None, None)
		original_container_command = container_command
		if self._interactive:
			print(f"Running container {prefix} step: {' '.join(container_command)}")
			container_command = [ "/bin/bash" ]

		container = await docker.create_container(docker_image_name = image_name, command = container_command, network = docker.networks[0], max_memory_mib = self._config.max_memory_mib, interactive = self._interactive, run_name_prefix = f"kartfire_{prefix}")
		if pre_run_hook is not None:
			pre_run_result = await pre_run_hook(container)

		if self._interactive:
			await container.cpdata(f"{' '.join(original_container_command)}\n".encode("utf-8"), "/root/.bash_history")

		await container.start()
		if self._interactive:
			await container.attach()

		t0 = time.time()
		status_code = await container.wait_timeout(timeout_secs)
		runtime_secs = time.time() - t0

		if status_code is None:
			# Docker container time timed out
			_log.debug("Docker container \"%s\" timed out after %.1f seconds (allowance %.1f seconds)", prefix, runtime_secs, timeout_secs)
			testrun_status = TestrunStatus.Terminated
		elif status_code == 0:
			_log.debug("Docker container \"%s\" exited normally.", prefix)
			testrun_status = TestrunStatus.Finished
			if post_run_hook is not None:
				post_run_result = await post_run_hook(container)
		else:
			_log.debug("Docker container %s exited with status code %d.", prefix, status_code)
			testrun_status = TestrunStatus.Failed

		(stdout, stderr) = await container.logs()
		return ExecutionResult(stdout = stdout, stderr = stderr, testrun_status = testrun_status, runtime_secs = runtime_secs, pre_run_result = pre_run_result, post_run_result = post_run_result)

	async def _execute_build_step(self, docker: Docker, submission: "Submission"):
		async def pre_run_hook(container: "RunningDockerContainer"):
			with tempfile.NamedTemporaryFile(suffix = ".tar") as tmp:
				await submission.create_submission_tarfile(tmp.name)
				await container.cp(tmp.name, self._DEFS["container_submission_tar_file"])

			container_meta = {
				"container_dut_dir":				"/dut",
				"container_submission_tar_file":	"/dut.tar",
				"container_testcase_file":			"/testcases.json",
				"build_name":						self._config.build_name,
				"solution_name":					self._config.solution_name,
				"verbose":							2 if self._interactive else 0,
			}
			await container.write_json(container_meta, self._DEFS["container_meta_file"], pretty_print = self._interactive)

			await container.cp(self.container_testrunner_filename, self._DEFS["container_testrunner"])

		async def post_run_hook(container: "RunningDockerContainer"):
			committed_image_id = await container.commit(repository = "kartfire_testrun")
			return committed_image_id

		exec_result = await self._execute_docker_container_run(docker = docker, image_name = self._config.docker_container, container_command = [ "/container_testrunner", "--execute-build" ], prefix = f"bld_{submission.shortname}", pre_run_hook = pre_run_hook, post_run_hook = post_run_hook, timeout_secs = self._config.max_build_time_secs)
		self._evaluate_docker_stdout(exec_result)
		return exec_result

	async def _execute_run_step(self, docker: Docker, submission: "Submission", collection: "TestcaseCollection", base_image_name: str):
		async def pre_run_hook(container: "RunningDockerContainer"):
			container_testcases = {
				"testcases": { str(testcase.tc_id): testcase.guest_dict() for testcase in collection },
			}
			await container.write_json(container_testcases, self._DEFS["container_testcase_file"], pretty_print = self._interactive)

		timeout = self._determine_runtime_allowance_secs(collection)
		return await self._execute_docker_container_run(docker = docker, image_name = base_image_name, container_command = [ "/container_testrunner", "--execute-run" ], prefix = f"run_{submission.shortname}", pre_run_hook = pre_run_hook, timeout_secs = timeout)

	async def _run_submission(self, submission: "Submission"):
		async with self._process_semaphore:
			_log.info("Starting testing of submission \"%s\"", submission)

			build_constraints = BuildConstraints(runtime_allowance_secs = self._config.max_build_time_secs)
			container_image_metadata = ContainerImageMetadata.collect(self._config.docker_container, self.docker)
			multirun_id = self._db.create_multirun(submission, build_constraints = build_constraints, container_image_metadata = container_image_metadata)
			self._db.commit()

			async with self.docker as docker:
				await self._initialize_docker_env(docker)

				build_result = await self._execute_build_step(docker, submission)
				self._db.update_multirun_build_status(multirun_id, build_result)
				self._db.commit()

				for callback in self._submission_build_finished_callbacks:
					callback(multirun_id)

				if build_result.testrun_status == TestrunStatus.Finished:
					# Only continue running tests if build actually worked
					commited_base_image_id = build_result.post_run_result

					run_ids = [ ]
					for collection in self._testcase_collections:
						run_constraints = RunConstraints(runtime_allowance_secs = self._determine_runtime_allowance_secs(collection), max_permissible_ram_mib = self._config.max_memory_mib)

						run_id = self._db.create_testrun(multirun_id, collection, run_constraints = run_constraints)
						run_ids.append(run_id)
						self._db.commit()
						run_result = await self._execute_run_step(docker, submission, collection, base_image_name = commited_base_image_id)
						self._evaluate_docker_stdout(run_result, run_id, collection)
						self._db.commit()
						for callback in self._submission_run_finished_callbacks:
							callback(submission, run_id)
			for callback in self._submission_multirun_finished_callbacks:
				callback(submission, multirun_id)

			self._db.close_multirun(multirun_id)
			self._db.commit()

	async def _run(self, submissions: list["Submission"]):
		self._process_semaphore = asyncio.Semaphore(self._concurrent_process_count)
		_log.debug("Now testing %d submission(s) against %d collections", len(submissions), len(self._testcase_collections))
		async with asyncio.TaskGroup() as task_group:
			for submission in submissions:
				task_group.create_task(self._run_submission(submission))

	def run(self, submissions: list["Submission"]):
		return asyncio.run(self._run(submissions))
