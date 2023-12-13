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

import json
from .Testcase import Testcase
from .Exceptions import UnsupportedFileException

class TestcaseCollection():
	def __init__(self, testcases: list[dict], test_fixture_config: "TestFixtureConfig"):
		self._testcases = [ Testcase(testcase, test_fixture_config) for testcase in testcases ]
		self._config = test_fixture_config

	@classmethod
	def load_from_file(cls, filename: str, test_fixture_config: "TestFixtureConfig"):
		with open(filename) as f:
			json_file = json.load(f)
			if json_file["meta"]["type"] == "testcases":
				return cls(json_file["content"], test_fixture_config)
			else:
				raise UnsupportedFileException("Unsupported file type \"{json_file['meta']['type']}\" provided.")

	@property
	def testcase_count(self):
		return len(self._testcases)

	def __iter__(self):
		return iter(self._testcases)
