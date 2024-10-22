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
	def __init__(self, testcase_data: dict, test_fixture_config: "TestFixtureConfig"):
		self._testcase_data = testcase_data
		self._config = test_fixture_config
		self._testcases_by_name = self._generate_testcases_dict()

	def _generate_testcases_dict(self) -> dict:
		testcases_by_name = collections.OrderedDict()
		for (testcase_no, testcase_data) in enumerate(self._testcase_data["content"], 1):
			testcase_name = f"{self._testcase_data['meta']['name']}-{testcase_no:03d}"
			testcase = Testcase(testcase_name, testcase_data, self._config)
			testcases_by_name[testcase.name] = testcase
		return testcases_by_name

	@property
	def testcase_count(self):
		return len(self._testcases_by_name)

	@property
	def testcases_by_name(self):
		return self._testcases_by_name

	@classmethod
	def load_from_file(cls, filename: str, test_fixture_config: "TestFixtureConfig"):
		with open(filename) as f:
			json_file = json.load(f)
		if json_file["meta"]["type"] == "testcases":
			return cls(testcase_data = json_file, test_fixture_config = test_fixture_config)
		else:
			raise UnsupportedFileException("Unsupported file type \"{json_file['meta']['type']}\" provided.")

	def write_to_file(self, filename: str):
		with open(filename, "w") as f:
			json.dump(self._testcase_data, f, indent = "\t")
			f.write("\n")

	def get_batched(self, max_batch_size: int = 1):
		batch = [ ]
		for testcase in self:
			batch.append(testcase)
			if len(batch) >= max_batch_size:
				yield batch
				batch = [ ]
		if len(batch) > 0:
			yield batch

	def __iter__(self):
		return iter(self._testcases_by_name.values())
