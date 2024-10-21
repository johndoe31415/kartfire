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

import json
import collections
from .Testcase import Testcase
from .Exceptions import UnsupportedFileException

class TestcaseCollection():
	def __init__(self, testcases_by_name: dict[str, Testcase], test_fixture_config: "TestFixtureConfig"):
		self._testcases_by_name = testcases_by_name
		self._config = test_fixture_config

	@property
	def testcases_by_name(self):
		return self._testcases_by_name

	@classmethod
	def load_from_file(cls, filename: str, test_fixture_config: "TestFixtureConfig"):
		with open(filename) as f:
			json_file = json.load(f)
			if json_file["meta"]["type"] == "testcases":
				testcases = collections.OrderedDict()
				for (testcase_no, testcase_data) in enumerate(json_file["content"], 1):
					tc_name = f"{json_file['meta']['name']}-{testcase_no:03d}"
					tc = Testcase(tc_name, testcase_data, test_fixture_config)
					testcases[tc_name] = tc
				return cls(testcases, test_fixture_config)
			else:
				raise UnsupportedFileException("Unsupported file type \"{json_file['meta']['type']}\" provided.")

	@property
	def testcase_count(self):
		return len(self._testcases_by_name)

	def __iter__(self):
		return iter(self._testcases_by_name.values())
