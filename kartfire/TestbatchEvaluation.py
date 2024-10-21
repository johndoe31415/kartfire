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
import base64
import functools
from .Enums import TestcaseStatus, TestbatchStatus

class TestcaseEvaluation():
	def __init__(self, testbatch: "Testbatch", testcase: "Testcase", received_answer: dict, testcase_status: TestcaseStatus):
		self._testbatch = testbatch
		self._testcase = testcase
		self._received_answer = received_answer
		self._status = testcase_status

	@property
	def testcase(self) -> "Testcase":
		return self._testcase

	@property
	def status(self) -> TestcaseStatus:
		return self._status

	@functools.cached_property
	def details(self):
		match self.status:
			case TestcaseStatus.Passed:
				return None

			case TestcaseStatus.FailedWrongAnswer:
				return f"Testcase \"{self.testcase.name}\" failed because received answer was incorrect."

			case TestcaseStatus.NoAnswerProvided:
				return f"Testcase \"{self.testcase.name}\" failed because no answer was received."

			case TestcaseStatus.TestbatchFailedError:
				return f"Testcase \"{self.testcase.name}\" failed because contained testbatch failed: {self.testbatch.details}"


#			case TestcaseStatus.FailedTimeout:
#				return f"Timeout after {self._output['runtime_secs']:.1f} secs (allowance was {self._testcase.runtime_allowance_secs:.1f} secs)."

#			case TestcaseStatus.FailedErrorStatusCode:
#				if self._output["exception_msg"] is not None:
#					return f"Process terminated with status code {self._output['returncode']}: {self._output['exception_msg']}"
#				else:
#					return f"Process terminated with status code {self._output['returncode']}."
#			case TestcaseStatus.FailedWrongAnswer:
#				return "Wrong answer received."

#			case TestcaseStatus.FailedRunError:
#				if self._output["exception_msg"] is not None:
#					return f"Run failed: {self._output['exception_msg']}"
#				else:
#					return "Run failed for unknown reason."



	def to_dict(self):
		result = {
			"definition": self._testcase.to_dict(),
			"received_answer": self._received_answer,
			"testcase_status": self.status.name,
		}
		if self.details is not None:
			result["details"] = self.details
		return result

class TestbatchEvaluation():
	def __init__(self, runner: "TestcaseRunner", testbatch_runner_result: dict):
		self._runner = runner
		self._result = testbatch_runner_result
		self._status = None
		self._parsed_stdout = None
		self._determine_testbatch_status()

	@property
	def status(self) -> TestbatchStatus:
		return self._status

	@property
	def testcase_count(self):
		return len(self._result["testcases"])

	@functools.cached_property
	def answer_count(self):
		if self._status != TestbatchStatus.Completed:
			return 0
		else:
			asked_testcases = set(self._result["testcases"])
			answered_testcases = set(self._result["results"].keys())
			return len(asked_testcases & answered_testcases)

	@property
	def details(self):
		return "TODOOOOOOOOOOO"

	def _determine_testbatch_status(self):
		if self._result is None:
			self._status = TestbatchStatus.ErrorTestrunFailed
		else:
			if self._result["results"]["timeout"]:
				self._status = TestbatchStatus.ProcessTimeout
			elif self._result["results"]["returncode"] is None:
				self._status = TestbatchStatus.ErrorTestrunFailed
			elif self._result["results"]["returncode"] != 0:
				self._status = TestbatchStatus.ErrorStatusCode
			else:
				try:
					self._parsed_stdout = json.loads(base64.b64decode(self._result["results"]["stdout"]))
					self._status = TestbatchStatus.Completed
				except json.decoder.JSONDecodeError:
					return TestbatchStatus.FailedUnparsableAnswer

	@property
	def runtime_secs(self):
		if self._result is None:
			return 0
		else:
			return self._result["results"]["runtime_secs"]

	def get_testcase_result(self, testcase_name: str):
		received_answer = None
		testcase = self._runner[testcase_name]
		if self._status != TestbatchStatus.Completed:
			testcase_status = TestcaseStatus.TestbatchFailedError
		else:
			have_answer = testcase.name in self._parsed_stdout
			if have_answer:
				received_answer = self._parsed_stdout[testcase.name]
				expected_answer = testcase.testcase_answer
				if received_answer == expected_answer:
					testcase_status = TestcaseStatus.Passed
				else:
					testcase_status = TestcaseStatus.FailedWrongAnswer
			else:
				testcase_status = TestcaseStatus.NoAnswerProvided
		return TestcaseEvaluation(self, testcase, received_answer, testcase_status)

	@property
	def proc_details(self):
		if self._result is None:
			return None
		else:
			stdout = base64.b64decode(self._result["stdout"])
			stderr = base64.b64decode(self._result["stderr"])
			return {
				"stdout": stdout.decode("utf-8", errors = "replace"),
				"stdout_length": self._result["stdout_length"],
				"stdout_truncated": len(stdout) != self._result["stdout_length"],

				"stderr": stderr.decode("utf-8", errors = "replace"),
				"stderr_length": self._result["stderr_length"],
				"stderr_truncated": len(stderr) != self._result["stderr_length"],
			}

	def __iter__(self):
		for testcase_name in self._result["testcases"]:
			yield self.get_testcase_result(testcase_name)

	def to_dict(self):
		return {
			"testbatch_status": self.status.name,
			"runtime_secs": self.runtime_secs,
			"testcases": [ testcase_evaluation.to_dict() for testcase_evaluation in self ],
		}
