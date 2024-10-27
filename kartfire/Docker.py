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
import time
import tempfile
import json
import asyncio
import subprocess
import collections
from .Tools import ExecTools

class DockerNetwork():
	def __init__(self, docker: "Docker", network_id: str, allow_wan_access: bool):
		self._docker = docker
		self._network_id = network_id
		self._allow_wan_access = allow_wan_access

	@property
	def network_id(self):
		return self._network_id

	@property
	def allow_wan_access(self):
		return self._allow_wan_access

	async def rm(self):
		cmd = [ self._docker.executable, "network", "rm", self.network_id ]
		await ExecTools.async_check_call(cmd, stdout = subprocess.DEVNULL)

	def __repr__(self):
		return f"Network<ID {self.network_id[:8]}>"

class RunningDockerContainer():
	def __init__(self, docker: "Docker", container_id: str):
		self._docker = docker
		self._container_id = container_id

	@property
	def container_id(self):
		return self._container_id

	async def inspect(self):
		cmd = [ self._docker.executable, "inspect", self._container_id ]
		output = await ExecTools.async_check_output(cmd)
		return json.loads(output)[0]

	async def cpdata(self, content: bytes, container_filename: str):
		with tempfile.NamedTemporaryFile() as f:
			f.write(content)
			f.flush()
			await self.cp(f.name, container_filename)

	async def cp(self, local_filename: str, container_filename: str):
		cmd = [ self._docker.executable, "cp", local_filename, f"{self._container_id}:{container_filename}" ]
		await ExecTools.async_check_call(cmd, stdout = subprocess.DEVNULL)

	async def start(self):
		cmd = [ self._docker.executable, "start", self._container_id ]
		await ExecTools.async_check_call(cmd, stdout = subprocess.DEVNULL)

	async def attach(self):
		cmd = [ self._docker.executable, "attach", self._container_id ]
		await ExecTools.async_call(cmd)

	async def wait(self):
		cmd = [ self._docker.executable, "wait", self._container_id ]
		return int(await ExecTools.async_check_output(cmd))

	async def logs(self):
		cmd = [ self._docker.executable, "logs", self._container_id ]
		return await ExecTools.async_check_communicate(cmd)

	async def stop(self):
		cmd = [ self._docker.executable, "stop", self._container_id ]
		await ExecTools.async_check_call(cmd, stdout = subprocess.DEVNULL)

	async def rm(self):
		cmd = [ self._docker.executable, "rm", self._container_id ]
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

	def __repr__(self):
		return f"Container<ID {self.container_id[:8]}>"

class Docker():
	def __init__(self, docker_executable: str = "docker"):
		self._docker_executable = docker_executable
		self._cleanup_tasks = collections.defaultdict(list)

	@property
	def executable(self):
		return self._docker_executable

	async def create_container(self, docker_image_name: str, command: list, network: DockerNetwork, network_alias: str | None = None, max_memory_mib: int | None = None, interactive: bool = False, auto_cleanup: bool = True):
		# Create docker container, but do not start yet
		cmd = [ self._docker_executable, "create" ]
		cmd += [ "--network", network.network_id ]
		if not network.allow_wan_access:
			cmd += [ "--dns", "0.0.0.0", "--dns-search", "localdomain" ]
		if interactive:
			cmd += [ "--tty", "--interactive" ]
		if network_alias is not None:
			cmd += [ "--network-alias", network_alias ]
		if max_memory_mib is not None:
			cmd += [ f"--memory={max_memory_mib}m" ]
		cmd += [ docker_image_name ]
		cmd += command
		container_id = (await ExecTools.async_check_output(cmd)).decode("ascii").rstrip("\r\n")
		running_container = RunningDockerContainer(self, container_id)
		if auto_cleanup:
			self._cleanup_tasks[0].append(running_container.stop())
			self._cleanup_tasks[1].append(running_container.rm())
		return running_container

	async def create_network(self, network_name: str | None = None, allow_inter_container_connectivity: bool = True, allow_wan_access: bool = False, auto_cleanup: bool = True):
		if network_name is None:
			network_name = f"kartfire_{os.urandom(8).hex()}"
		cmd = [ self._docker_executable, "network", "create" ]
		cmd += [ "-d", "bridge" ]
		cmd += [ "--opt", f"com.docker.network.bridge.enable_icc={'true' if allow_inter_container_connectivity else 'false'}" ]
		cmd += [ "--opt", f"com.docker.network.bridge.enable_ip_masquerade={'true' if allow_wan_access else 'false'}" ]
		cmd += [ network_name ]
		network_id = (await ExecTools.async_check_output(cmd)).decode("ascii").rstrip("\r\n")
		network = DockerNetwork(self, network_id, allow_wan_access = allow_wan_access)
		if auto_cleanup:
			self._cleanup_tasks[1].append(network.rm())
		return network

	def inspect_image(self, image_name: str):
		cmd = [ self.executable, "image", "inspect", image_name ]
		output = subprocess.check_output(cmd)
		return json.loads(output)[0]

	async def __aenter__(self):
		return self

	async def _execute_task_list(self, task_list: list["coroutine"], max_concurrent_tasks: int = 20):
		semaphore = asyncio.Semaphore(max_concurrent_tasks)
		async def execute_task(task):
			async with semaphore:
				await task
		execution_tasks = [ asyncio.create_task(execute_task(task)) for task in task_list ]
		await asyncio.gather(*execution_tasks)

	async def __aexit__(self, *args):
		for (order_id, task_list) in sorted(self._cleanup_tasks.items()):
			await self._execute_task_list(task_list)


if __name__ == "__main__":
	async def main_run():
		print("Started main.")
		async with Docker() as docker:
			network = await docker.create_network()
			print(f"Using network: {network}")
			containers = [ ]
			for i in range(10):
				container = await docker.create_container(docker_image_name = "ghcr.io/johndoe31415/labwork-docker:master", command = [ "sleep", "5" ], network = network)
				containers.append(container)
			print(containers)
			print("Starting all...")
			await asyncio.gather(*[ container.start() for container in containers])
			print("Waiting for finish...")
			await asyncio.gather(*[ container.wait_timeout(20) for container in containers])
			print("Awaited their exit, context manager cleans up.")
		print("Exited main.")

	asyncio.run(main_run())
