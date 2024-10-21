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
import multiprocessing

class TestFixtureConfig():
	_DEFAULT_FIXTURE_FILENAME = "kartfire_test_fixture.json"

	def __init__(self, config: dict | None = None):
		if config is None:
			config = { }
		self._config = config

	@classmethod
	def load_from_file(cls, filename: str | None):
		if filename is not None:
			with open(filename) as f:
				return cls(json.load(f))
		elif (filename is None) and os.path.isfile(cls._DEFAULT_FIXTURE_FILENAME):
			return cls.load_from_file(cls._DEFAULT_FIXTURE_FILENAME)
		else:
			return cls()

	@property
	def docker_executable(self):
		return self._config.get("docker_executable", "docker")

	@property
	def docker_container(self):
		return self._config.get("docker_container", "ghcr.io/johndoe31415/labwork-docker:master")

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
		return self._config.get("max_concurrent_processes", multiprocessing.cpu_count())

	@property
	def max_setup_time_secs(self):
		return self._config.get("max_setup_time_secs", 30)

	@property
	def minimum_testcase_time(self):
		return self._config.get("minimum_testcase_time", 0.5)

	@property
	def reference_time_factor(self):
		return self._config.get("reference_time_factor", 10)

	@property
	def allow_network(self):
		return self._config.get("allow_network", False)

	@property
	def interactive(self):
		return self._config.get("interactive", False)

	@interactive.setter
	def interactive(self, value: bool):
		self._config["interactive"] = value

	@property
	def testbatch_maxsize(self):
		return self._config.get("testbatch_maxsize", 1)
