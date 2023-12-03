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
import tempfile
from .Exceptions import InvalidSubmissionException
from .DockerRun import DockerRun
from .ValidationResult import ValidationResult
from .Tools import ExecTools, JSONTools

class Submission():
	def __init__(self, submission_directory):
		self._submission_dir = os.path.realpath(submission_directory)
		if not os.path.isdir(self._submission_dir):
			raise InvalidSubmissionException(f"{self._submission_dir} is not a directory")
		self._validation_result = ValidationResult()

	async def _create_submission_tarfile(self, tarfile_name):
		await ExecTools.async_check_call([ "tar", "-C", self._submission_dir, "-c", "-f", tarfile_name, "." ])

	async def run(self, runner: "TestcaseRunner"):
		dut_params = {
			"max_build_time_secs": runner.config.max_build_time_secs,
			"limit_stdout_bytes": 5000,
		}

		docker = DockerRun(docker_executable = runner.config.docker_executable)
		await docker.create(docker_image_name = runner.config.docker_container, command = [ "/container_testrunner", JSONTools.encode_b64(dut_params) ], max_memory_mib = runner.config.max_memory_mib, allow_network = runner.config.allow_network)
		await docker.cp("container_testrunner", "/container_testrunner")			# TODO
		with tempfile.NamedTemporaryFile(suffix = ".tar") as tmp:
			await self._create_submission_tarfile(tmp.name)
			await docker.cp(tmp.name, "/dut.tar")
		await docker.cpdata(runner.client_testcase_data, "/dut.json")
		await docker.start()

		finished = await docker.wait_timeout(runner.total_maximum_runtime_secs)

