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
from .Enums import TestcaseStatus
from .Exceptions import InvalidTestcaseException
from .Tools import JSONTools

class Testcase():
	def __init__(self, name: str, testcase: dict, test_fixture_config: "TestFixtureConfig"):
		self._name = name
		if not isinstance(testcase, dict):
			raise InvalidTestcaseException("Testcase definition must be a dictionary.")
		if "testcase_data" not in testcase:
			raise InvalidTestcaseException("Testcase definition is missing the 'testcase_data' key.")
		if "testcase_answer" not in testcase:
			testcase["testcase_answer"] = { }
		if "runtime_allowance_secs" not in testcase:
			raise InvalidTestcaseException("Testcase definition is missing the 'runtime_allowance_secs' key.")
		if "action" not in testcase["testcase_data"]:
			raise InvalidTestcaseException("Testcase definition is missing the 'testcase_data.action' key.")
		self._tc = testcase
		self._config = test_fixture_config

	@property
	def name(self):
		return self._name

	@property
	def guest_data(self):
		"""This is the data that the guest receives inside the runner. May not
		contain solution data."""
		return {
			"name": self.name,
			"testcase_data": self.testcase_data,
			"runtime_allowance_secs": self.runtime_allowance_secs,
		}

	@property
	def testcase_id(self):
		return JSONTools.jsonhash(self.testcase_data)

	@property
	def action(self):
		return self.testcase_data.get("action")

	@property
	def testcase_data(self):
		return self._tc["testcase_data"]

	@property
	def testcase_answer(self):
		return self._tc["testcase_answer"]

	@testcase_answer.setter
	def testcase_answer(self, correct_answer: dict):
		self._tc["testcase_answer"] = correct_answer

	@property
	def runtime_allowance_secs(self):
		return (self.runtime_allowance_secs_unscaled * self._config.reference_time_factor) + self._config.minimum_testcase_time

	@property
	def runtime_allowance_secs_unscaled(self):
		return self._tc["runtime_allowance_secs"]

	@property
	def action(self):
		return self.testcase_data["action"]

	def to_dict(self):
		return {
			"id": self.testcase_id,
			"testcase_data": self.testcase_data,
			"testcase_answer": self.testcase_answer,
			"runtime_allowance_secs": self.runtime_allowance_secs,
		}
