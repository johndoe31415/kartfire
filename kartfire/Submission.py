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

import os
import json
import tempfile
import functools
import logging
from .Exceptions import InvalidSubmissionException
from .Docker import Docker
from .Tools import ExecTools, GitTools
from .TestrunnerOutput import TestrunnerOutput
from .Enums import TestrunStatus

_log = logging.getLogger(__spec__.name)

class Submission():
	def __init__(self, submission_directory: str):
		self._submission_dir = os.path.realpath(submission_directory)
		if not os.path.isdir(self._submission_dir):
			raise InvalidSubmissionException(f"{self._submission_dir} is not a directory")

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
		return meta

	async def _create_submission_tarfile(self, tarfile_name):
		await ExecTools.async_check_call([ "tar", "-C", self._submission_dir, "-c", "-f", tarfile_name, "." ])

	async def run(self, runner: "TestcaseRunner", interactive: bool = False):
		local_container_testrunner = "/container_testrunner"
		local_container_parameter_filename = "/container_testrunner.json"
		container_parameters = {
			"meta": {
				"limit_stdout_bytes":			128 * 1024,
				"local_testcase_tar_file":		"/dut.tar",
				"setup_name":					runner.config.setup_name,
				"max_setup_time_secs":			runner.config.max_setup_time_secs,
				"solution_name":				runner.config.solution_name,
				"local_dut_dir":				"/dut",
				"local_testcase_filename":		"/local_testcases.json",
				"debug":						interactive,
			},
			"testbatches": runner.guest_testbatch_data,
		}


		command = [ local_container_testrunner, local_container_parameter_filename ]
		if interactive:
			print(f"Would have run: {' '.join(command)}")
			command = [ "/bin/bash" ]

		_log.debug("Creating docker container to run submission %s", str(self))
		testrunner_output = TestrunnerOutput()

		async with Docker(docker_executable = runner.config.docker_executable) as docker:
			network = await docker.create_network()

			# Start all dependent servers (e.g., a server container that the
			# submission needs to connect to)
			for (server_alias, server_config) in runner.required_server_containers.items():
				_log.debug("Starting dependent server %s with config %s.", server_alias, str(server_config))
				server_container = await docker.create_container(docker_image_name = server_config["image"], command = server_config["command"], network = network, network_alias = server_alias)
				await server_container.start()

			container = await docker.create_container(docker_image_name = runner.config.docker_container, command = command, network = network, max_memory_mib = runner.config.max_memory_mib, interactive = interactive)
			await container.cp(self.container_testrunner_filename, local_container_testrunner)
			with tempfile.NamedTemporaryFile(suffix = ".tar") as tmp:
				await self._create_submission_tarfile(tmp.name)
				await container.cp(tmp.name, container_parameters["meta"]["local_testcase_tar_file"])
			await container.cpdata(json.dumps(container_parameters).encode("utf-8"), local_container_parameter_filename)
			await container.start()
			if interactive:
				await container.attach()

			testrunner_output.status = TestrunStatus.Completed
			finished = await container.wait_timeout(runner.total_maximum_runtime_secs)
			if finished is None:
				# Docker container time timed out
				testrunner_output.status = TestrunStatus.ContainerTimeout
				_log.debug("Docker container with submission %s timed out after %d seconds", str(self), runner.total_maximum_runtime_secs)
				return testrunner_output
			_log.debug("Docker container with submission %s exited normally.", str(self))

			logs = await container.logs()
			testrunner_output.logs = logs
			#testrunner_output.dump(verbose = True)
			if finished != 0:
				# Docker container errored
				testrunner_output.status = TestrunStatus.ErrorStatusCode
				return testrunner_output
			return testrunner_output

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
