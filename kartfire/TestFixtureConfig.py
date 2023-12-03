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

class TestFixtureConfig():
	def __init__(self, config: dict):
		self._config = config

	@classmethod
	def load_from_file(cls, filename):
		with open(filename) as f:
			return cls(json.load(f))

	@property
	def docker_executable(self):
		return self._config.get("docker_executable", "docker")

	@property
	def setup_name(self):
		return self._config.get("setup_name", "setup")

	@property
	def solution_name(self):
		return self._config.get("solution_name", "solution")

	@property
	def max_memory_mib(self):
		return self._config.get("max_memory_mib", 1024)

	@property
	def host_memory_usage_percent(self):
		return self._config.get("host_memory_usage_percent", 100)

	@property
	def max_concurrent_processes(self):
		return self._config.get("max_concurrent_processes", 8)

	@property
	def max_build_time_secs(self):
		return self._config.get("max_build_time_secs", 30)

	@property
	def minimum_testcase_time(self):
		return self._config.get("minimum_testcase_time", 0.5)

	@property
	def reference_time_factor(self):
		return self._config.get("reference_time_factor", 10)
