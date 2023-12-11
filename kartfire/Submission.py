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

import os
import json
import tempfile
import functools
import contextlib
from .Exceptions import InvalidSubmissionException
from .DockerRun import DockerRun
from .Tools import ExecTools, JSONTools
from .TestrunnerOutput import TestrunnerOutput
from .Enums import TestrunStatus

class Submission():
	def __init__(self, submission_directory):
		self._submission_dir = os.path.realpath(submission_directory)
		if not os.path.isdir(self._submission_dir):
			raise InvalidSubmissionException(f"{self._submission_dir} is not a directory")

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

	@contextlib.asynccontextmanager
	async def _start_docker_instance(self, config: "TestFixtureConfig"):
		docker = DockerRun(docker_executable = config.docker_executable)
		yield docker
		await docker.stop()
		await docker.rm()

	async def run(self, runner: "TestcaseRunner"):
		local_container_testrunner = "/container_testrunner"
		dut_params = {
			"limit_stdout_bytes": 8 * 1024,
			"local_testcase_json_file": "/dut.json",
			"local_testcase_tar_file": "/dut.tar",
			"setup_name": runner.config.setup_name,
			"max_setup_time_secs": runner.config.max_setup_time_secs,
			"solution_name": runner.config.solution_name,
		}

		testrunner_output = TestrunnerOutput()
		async with self._start_docker_instance(runner.config) as docker:
			await docker.create(docker_image_name = runner.config.docker_container, command = [ local_container_testrunner, JSONTools.encode_b64(dut_params) ], max_memory_mib = runner.config.max_memory_mib, allow_network = runner.config.allow_network)
			await docker.cp("container_testrunner", local_container_testrunner)			# TODO source
			with tempfile.NamedTemporaryFile(suffix = ".tar") as tmp:
				await self._create_submission_tarfile(tmp.name)
				await docker.cp(tmp.name, dut_params["local_testcase_tar_file"])
			await docker.cpdata(runner.client_testcase_data, dut_params["local_testcase_json_file"])
			await docker.start()

			testrunner_output.status = TestrunStatus.Completed
			finished = await docker.wait_timeout(runner.total_maximum_runtime_secs)
			if finished is None:
				# Docker container time timed out
				testrunner_output.status = TestrunStatus.Timeout
				return testrunner_output

			logs = await docker.logs()
			testrunner_output.logs = logs
#			testrunner_output.dump(verbose = True)
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
			return f"{short_dir}: {meta['git']['branch']} / {meta['git']['commit'][:8]}"
		else:
			return short_dir
