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
from .CmdlineAction import CmdlineAction
from .Docker import Docker

class ActionScram(CmdlineAction):
	async def _stop_wait(self, container: "RunningDockerContainer"):
		await container.stop()
		await container.wait()

	async def _execute_scram(self, containers: list["RunningDockerContainer"]):
		async with asyncio.TaskGroup() as task_group:
			for container in containers:
				task_group.create_task(self._stop_wait(container))

	def run(self):
		docker = Docker()
		containers = list(docker.get_all_kartfire_containers())
		if len(containers) == 0:
			print("No kartfire processes found, no SCRAM necessary.")
			return 1

		yn = input(f"About to terminate {len(containers)} kartfire docker containers, continue (y/n)? ")
		if yn.lower() != "y":
			print("Aborted SCRAM.")
			return 2

		asyncio.run(self._execute_scram(containers))
		return 0
