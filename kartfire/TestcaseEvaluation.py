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
import base64
import functools
from .Enums import TestcaseStatus

class TestcaseEvaluation():
	def __init__(self, testcase: "Testcase", testcase_runner_output: dict):
		self._testcase = testcase
		self._output = testcase_runner_output

	@property
	def testcase(self) -> "Testcase":
		return self._testcase

	@functools.cached_property
	def received_answer(self):
		try:
			return json.loads(base64.b64decode(self._output["stdout"]))
		except json.decoder.JSONDecodeError:
			return None

	@functools.cached_property
	def status(self):
		if self._output is None:
			return TestcaseStatus.FailedRunError
		else:
			if self._output["timeout"]:
				return TestcaseStatus.FailedTimeout
			elif self._output["returncode"] is None:
				return TestcaseStatus.FailedRunError
			elif self._output["returncode"] != 0:
				return TestcaseStatus.FailedErrorStatusCode
			else:
				try:
					parsed_stdout = json.loads(base64.b64decode(self._output["stdout"]))
					if parsed_stdout != self._testcase.testcase_answer:
						return TestcaseStatus.FailedWrongAnswer
					else:
						return TestcaseStatus.Passed
				except json.decoder.JSONDecodeError:
					return TestcaseStatus.FailedUnparsableAnswer

	@property
	def runtime_secs(self):
		if self._output is None:
			return 0
		else:
			return self._output["runtime_secs"]

	@functools.cached_property
	def details(self):
#		print(self.status)
#		print(self._output)
		match self.status:
			case TestcaseStatus.FailedTimeout:
				return f"Timeout after {self._output['runtime_secs']:.1f} secs (allowance was {self._testcase.runtime_allowance_secs:.1f} secs)."

			case TestcaseStatus.FailedErrorStatusCode:
				if self._output["exception_msg"] is not None:
					return f"Process terminated with status code {self._output['returncode']}: {self._output['exception_msg']}"
				else:
					return f"Process terminated with status code {self._output['returncode']}."

			case TestcaseStatus.FailedWrongAnswer:
				return "Wrong answer received."

			case TestcaseStatus.FailedRunError:
				if self._output["exception_msg"] is not None:
					return f"Run failed: {self._output['exception_msg']}"
				else:
					return "Run failed for unknown reason."

			case TestcaseStatus.Passed:
				return None

			case _:
#				print(self.status)
#				print(self._output)
#				fff
				return None

	@property
	def proc_details(self):
		if self._output is None:
			return None
		else:
			stdout = base64.b64decode(self._output["stdout"])
			stderr = base64.b64decode(self._output["stderr"])
			return {
				"stdout": stdout.decode("utf-8", errors = "replace"),
				"stdout_length": self._output["stdout_length"],
				"stdout_truncated": len(stdout) != self._output["stdout_length"],

				"stderr": stderr.decode("utf-8", errors = "replace"),
				"stderr_length": self._output["stderr_length"],
				"stderr_truncated": len(stderr) != self._output["stderr_length"],
			}

	def to_dict(self):
		result = {
			"status": self.status.name,
			"runtime_secs": self.runtime_secs,
			"testcase": self._testcase.to_dict(),
			"received_answer": self.received_answer,
		}
		if self.details is not None:
			result["details"] = self.details
		if self.status != TestcaseStatus.Passed:
			result["proc_details"] = self.proc_details
		return result
