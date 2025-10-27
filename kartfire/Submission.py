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
import sys
import json
import tempfile
import functools
import dataclasses
import logging
from .Exceptions import InvalidSubmissionException
from .Docker import Docker
from .Tools import ExecTools, GitTools, MiscTools
from .Enums import TestrunStatus

_log = logging.getLogger(__spec__.name)

class Submission():
	@dataclasses.dataclass
	class SubmissionRunResult():
		submission: "Submission"
		stdout: bytes
		stderr: bytes
		testrun_status: TestrunStatus
		error_details: str | None = None

	def __init__(self, submission_directory: str):
		self._submission_dir = os.path.realpath(submission_directory)
		if not os.path.isdir(self._submission_dir):
			raise InvalidSubmissionException(f"{self._submission_dir} is not a directory")

	@property
	def shortname(self):
		return os.path.basename(self._submission_dir)

	@property
	def container_testrunner_filename(self):
		return os.path.realpath(os.path.dirname(__file__)) + "/container/container_testrunner"

	@functools.cached_property
	def meta_info(self):
		meta = { }
		if os.path.isdir(f"{self._submission_dir}/.git"):
			meta["git"] = GitTools.gitinfo(self._submission_dir)
		json_filename = f"{self._submission_dir}.json"
		if os.path.isfile(json_filename):
			with open(json_filename) as f:
				meta["json"] = json.load(f)
		meta["filetypes"] = MiscTools.determine_lines_by_file_extension(self._submission_dir)
		return meta

	async def _create_submission_tarfile(self, tarfile_name):
		await ExecTools.async_check_call([ "tar", "-C", self._submission_dir, "-c", "-f", tarfile_name, "." ])

	async def run(self, runner: "TestcaseRunner", interactive: bool = False):
		container_meta = {
			"container_dut_dir":				"/dut",
			"container_submission_tar_file":	"/dut.tar",
			"container_testcase_file":			"/testcases.json",

			"setup_name":						runner.config.setup_name,
			"max_setup_time_secs":				runner.config.max_setup_time_secs,
			"solution_name":					runner.config.solution_name,
			"max_runtime_secs":					123,

			"verbose":							2 if interactive else 0,
		}
		container_testcases = {
			"testcases": { str(testcase.tc_id): testcase.guest_dict() for testcase in runner.testcases },
		}

		original_container_command = [ "/container_testrunner" ]
		container_command = original_container_command
		if interactive:
			print(f"Trigger test runner using: {' '.join(container_command)}")
			container_command = [ "/bin/bash" ]

		_log.debug("Creating docker container to run submission \"%s\"", str(self))

		async with Docker(docker_executable = runner.config.docker_executable) as docker:
			network = await docker.create_network()

			# Start all dependent servers (e.g., a server container that the
			# submission needs to connect to)
			for (server_alias, server_config) in runner.testcases.dependencies.items():
				_log.debug("Starting dependent server %s with config %s.", server_alias, str(server_config))
				server_container = await docker.create_container(docker_image_name = server_config["image"], command = server_config["command"], network = network, network_alias = server_alias, run_name_prefix = f"hlp_{self.shortname}_{server_alias}")
				await server_container.start()

			container = await docker.create_container(docker_image_name = runner.config.docker_container, command = container_command, network = network, max_memory_mib = runner.config.max_memory_mib, interactive = interactive, run_name_prefix = f"run_{self.shortname}")
			await container.cp(self.container_testrunner_filename, "/container_testrunner")
			with tempfile.NamedTemporaryFile(suffix = ".tar") as tmp:
				await self._create_submission_tarfile(tmp.name)
				await container.cp(tmp.name, container_meta["container_submission_tar_file"])
			await container.write_json(container_meta, "/meta.json", pretty_print = interactive)
			await container.write_json(container_testcases, container_meta["container_testcase_file"], pretty_print = interactive)
			if interactive:
				await container.cpdata(f"{' '.join(original_container_command)}\n".encode("utf-8"), "/root/.bash_history")
			await container.start()
			if interactive:
				await container.attach()

			finished = await container.wait_timeout(runner.total_maximum_runtime_secs)
			if finished is None:
				# Docker container time timed out
				_log.debug("Docker container with submission \"%s\" timed out after %d seconds", str(self), runner.total_maximum_runtime_secs)
				testrun_status = TestrunStatus.Terminated
			elif finished == 0:
				_log.debug("Docker container with submission \"%s\" exited normally.", str(self))
				testrun_status = TestrunStatus.Finished
			else:
				_log.debug("Docker container with submission \"%s\" exited with status code %d.", str(self), finished)
				testrun_status = TestrunStatus.Failed

			(stdout, stderr) = await container.logs()
			return self.SubmissionRunResult(submission = self, stdout = stdout, stderr = stderr, testrun_status = testrun_status)

	def to_dict(self):
		return {
			"dirname": self._submission_dir,
			"meta": self.meta_info,
		}

	def __str__(self):
		short_dir = os.path.basename(self._submission_dir)
		meta = self.meta_info
		if ("json" in meta) and ("text" in meta["json"]):
			return f"{short_dir}: {meta['json']['text']}"
		elif "git" in meta:
			if meta["git"]["empty"]:
				return f"{short_dir}: empty Git repository"
			elif not meta["git"]["has_branch"]:
				return f"{short_dir}: no branch {meta['git']['branch']}"
			else:
				return f"{short_dir}: {meta['git']['branch']} / {meta['git']['commit'][:8]}"
		else:
			return short_dir
