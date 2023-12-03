#	kartfire - The X.509 Swiss Army Knife white-hat certificate toolkit
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

import json
from .Exceptions import DockerFailureException
from .Tools import ExecTools

class DockerRun():
	def __init__(self, docker_executable: str = "docker"):
		self._docker_executable = docker_executable
		self._container_id = None

	async def create(self, docker_image_name: str, command: list, max_memory_mib: int | None = None, allow_network: bool = False):
		assert(self._container_id is None)
		# Start docker container
		cmd = [ self._docker_executable, "create" ]
		if not allow_network:
				cmd += [ "--network", "nonat", "--dns", "0.0.0.0", "--dns-search", "localdomain" ]
#		cmd += [ "--name", f"testrun-{student['id'].lower()}" ]
		if max_memory_mib is not None:
			cmd += [ "--memory={max_memory_mib}m" ]
		cmd += [ docker_image_name ]
		cmd += command
		self._container_id = (await ExecTools.async_check_output(cmd)).decode("ascii").rstrip("\r\n")

	async def inspect(self):
		cmd = [ self._docker_executable, "inspect", self._container_id ]
		output = await ExecTools.async_check_output(cmd)
		return json.loads(output)[0]

	async def cp(self, local_filename: str, container_filename: str):
		cmd = [ self._docker_executable, "cp", local_filename, f"{self._container_id}:{container_filename}" ]
		await ExecTools.async_check_call(cmd)

	async def wait(self):
		cmd = [ self._docker_executable, "wait", self._container_id ]
		await ExecTools.async_check_call(cmd)

	async def logs(self):
		cmd = [ self._docker_executable, "logs", self._container_id ]
		await ExecTools.async_check_call(cmd)

	async def stop(self):
		cmd = [ self._docker_executable, "logs", self._container_id ]
		await ExecTools.async_check_call(cmd)

	async def rm(self):
		cmd = [ self._docker_executable, "rm", self._container_id ]
		await ExecTools.async_check_call(cmd)

	async def wait_timeout(self, timeout: float, check_interval: float = 1.0):
		end_time = time.time() + timeout
		while True:
			inspection_result = await self.inspect()
			if inspection_result["State"]["Status"] != "running":
				await self.wait()
				return True
			if time.time() > end_time:
				return False
			await asyncio.sleep(check_interval)
