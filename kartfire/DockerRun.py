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

import time
import tempfile
import json
import asyncio
import subprocess
from .Exceptions import DockerFailureException
from .Tools import ExecTools

class DockerRun():
	def __init__(self, docker_executable: str = "docker"):
		self._docker_executable = docker_executable
		self._container_id = None

	async def create(self, docker_image_name: str, command: list, max_memory_mib: int | None = None, allow_network: bool = False, interactive: bool = False):
		assert(self._container_id is None)
		# Start docker container
		cmd = [ self._docker_executable, "create" ]
		if not allow_network:
			cmd += [ "--network", "nonat", "--dns", "0.0.0.0", "--dns-search", "localdomain" ]
		if interactive:
			cmd += [ "--tty", "--interactive" ]
#		cmd += [ "--name", f"testrun-{student['id'].lower()}" ]
		if max_memory_mib is not None:
			cmd += [ f"--memory={max_memory_mib}m" ]
		cmd += [ docker_image_name ]
		cmd += command
		self._container_id = (await ExecTools.async_check_output(cmd)).decode("ascii").rstrip("\r\n")

	async def inspect(self):
		cmd = [ self._docker_executable, "inspect", self._container_id ]
		output = await ExecTools.async_check_output(cmd)
		return json.loads(output)[0]

	async def cpdata(self, content: bytes, container_filename: str):
		with tempfile.NamedTemporaryFile() as f:
			f.write(content)
			f.flush()
			await self.cp(f.name, container_filename)

	async def cp(self, local_filename: str, container_filename: str):
		cmd = [ self._docker_executable, "cp", local_filename, f"{self._container_id}:{container_filename}" ]
		await ExecTools.async_check_call(cmd, stdout = subprocess.DEVNULL)

	async def start(self):
		cmd = [ self._docker_executable, "start", self._container_id ]
		await ExecTools.async_check_call(cmd, stdout = subprocess.DEVNULL)

	async def attach(self):
		cmd = [ self._docker_executable, "attach", self._container_id ]
		await ExecTools.async_call(cmd)

	async def wait(self):
		cmd = [ self._docker_executable, "wait", self._container_id ]
		return int(await ExecTools.async_check_output(cmd))

	async def logs(self):
		cmd = [ self._docker_executable, "logs", self._container_id ]
		return await ExecTools.async_check_communicate(cmd)

	async def stop(self):
		cmd = [ self._docker_executable, "stop", self._container_id ]
		await ExecTools.async_check_call(cmd, stdout = subprocess.DEVNULL)

	async def rm(self):
		cmd = [ self._docker_executable, "rm", self._container_id ]
		await ExecTools.async_check_call(cmd, stdout = subprocess.DEVNULL)

	async def wait_timeout(self, timeout: float, check_interval: float = 1.0):
		end_time = time.time() + timeout
		while True:
			inspection_result = await self.inspect()
			if inspection_result["State"]["Status"] != "running":
				return await self.wait()
			if time.time() > end_time:
				return None
			await asyncio.sleep(check_interval)
