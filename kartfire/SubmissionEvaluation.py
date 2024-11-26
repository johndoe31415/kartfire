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

import collections
import functools
import kartfire
from .SubprocessExecutionResult import SubprocessExecutionResult
from .Enums import ExecutionResult, TestrunStatus, TestcaseStatus

class Statistics():
	def __init__(self, submission_evaluation: "SubmissionEvaluation", group_key_fnc: "callable"):
		self._submission_evaluation = submission_evaluation
		self._group_key_fnc = group_key_fnc
		self._statistics = { }
		self._compute()

	def _account_statistic_of(self, key: str, testcase_evaluation: "TestcaseEvaluation"):
		if key not in self._statistics:
			self._statistics[key] = {
				"total": 0,
				"passed": 0,
				"failed": 0,
				"breakdown": collections.Counter(),
			}
		self._statistics[key]["total"] += 1
		if testcase_evaluation.status == TestcaseStatus.Passed:
			self._statistics[key]["passed"] += 1
		else:
			self._statistics[key]["failed"] += 1
		self._statistics[key]["breakdown"][testcase_evaluation.status.name] += 1

	def _compute(self):
		for testcase_evaluation in self._submission_evaluation:
			key = self._group_key_fnc(testcase_evaluation)
			self._account_statistic_of(key = "*", testcase_evaluation = testcase_evaluation)
			self._account_statistic_of(key = key, testcase_evaluation = testcase_evaluation)

	def to_dict(self) -> dict:
		return self._statistics

class TestbatchEvaluation():
	def __init__(self, testbatch_data: dict, testbatch_no: int, runner: "TestcaseRunner"):
		self._testbatch_data = testbatch_data
		self._testbatch_no = testbatch_no
		self._runner = runner
		self._process = SubprocessExecutionResult(self._testbatch_data["process"])

	@property
	def testbatch_no(self):
		  return self._testbatch_no

	@property
	def process(self):
		return self._process

	def __iter__(self):
		for testcase_name in self._testbatch_data["testcases"]:
			yield self._runner[testcase_name]


class TestcaseEvaluation():
	def __init__(self, testcase: "Testcase", received_answer: dict | None, testcase_status: TestcaseStatus, testbatch_evaluation: TestbatchEvaluation | None = None):
		self._testcase = testcase
		self._received_answer = received_answer
		self._status = testcase_status
		self._testbatch_evaluation = testbatch_evaluation

	@property
	def testcase(self) -> "Testcase":
		return self._testcase

	@property
	def testbatch_evaluation(self):
		return self._testbatch_evaluation

	@property
	def status(self) -> TestcaseStatus:
		return self._status

	@property
	def received_answer(self) -> dict:
		return self._received_answer

	@property
	def detail_text(self):
		match self.status:
			case TestcaseStatus.Passed:
				return f"passed"

			case TestcaseStatus.FailedWrongAnswer:
				return f"failed because received answer was incorrect"

			case TestcaseStatus.NoAnswerProvided:
				return f"failed because no answer was provided"

			case TestcaseStatus.BuildTimedOut:
				return f"build timed out"

			case TestcaseStatus.BuildFailure:
				return f"build failed"

			case TestcaseStatus.BatchFailedInvalidAnswerProvided:
				return f"batch {self._testbatch_evaluation.testbatch_no} failed (invalid answer type)"

			case TestcaseStatus.BatchFailedNotExecutable:
				return f"batch {self._testbatch_evaluation.testbatch_no} failed (DUT was not executable)"

			case TestcaseStatus.BatchFailedUnparsableAnswerProvided:
				return f"batch {self._testbatch_evaluation.testbatch_no} failed (answer not valid JSON)"

			case TestcaseStatus.BatchFailedReturnCode:
				return f"batch {self._testbatch_evaluation.testbatch_no} failed (nonzero return code)"

			case TestcaseStatus.BatchFailedTimeout:
				return f"batch {self._testbatch_evaluation.testbatch_no} failed (timeout)"

			case TestcaseStatus.BatchFailedExecExecption:
				return f"batch {self._testbatch_evaluation.testbatch_no} failed (exec not possible)"

			case TestcaseStatus.BatchFailedOutOfMemory:
				return f"batch {self._testbatch_evaluation.testbatch_no} failed (out of memory)"

			case TestcaseStatus.DockerRunFailed:
				return f"Docker run failed"

	def to_dict(self):
		result = {
			"definition": self._testcase.to_dict(),
			"received_answer": self._received_answer,
			"testcase_status": self.status.name,
			"detail_text": self.detail_text,
			"testbatch": None if self._testbatch_evaluation is None else self._testbatch_evaluation.testbatch_no
		}
		return result

class SubmissionEvaluation():
	def __init__(self, testrunner_output: "TestrunnerOutput", runner: "TestcaseRunner", submission: "Submission"):
		self._testrunner_output = testrunner_output
		self._runner = runner
		self._submission = submission
		self._evaluated_testcases = [ ]
		self._consolidate_results()

	@property
	def testcase_count(self):
		return len(self._evaluated_testcases)

	@functools.cached_property
	def passed_testcase_count(self):
		return sum(1 for testcase_evaluation in self if testcase_evaluation.status == TestcaseStatus.Passed)

	@property
	def failed_testcase_count(self):
		return self.testcase_count - self.passed_testcase_count

	def _judge_testcases_of_testbatch(self, testbatch_evaluation: TestbatchEvaluation, testcase_status: TestcaseStatus):
		for testcase in testbatch_evaluation:
			testcase_evaluation = TestcaseEvaluation(testcase = testcase, testbatch_evaluation = testbatch_evaluation, received_answer = None, testcase_status = testcase_status)
			self._evaluated_testcases.append(testcase_evaluation)

	def _judge_testcases_without_testbatch(self, testcases: "iterable", testcase_status: TestcaseStatus):
		for testcase in testcases:
			testcase_evaluation = TestcaseEvaluation(testcase = testcase, testbatch_evaluation = None, received_answer = None, testcase_status = testcase_status)
			self._evaluated_testcases.append(testcase_evaluation)

	def _consolidate_results(self):
		if self._testrunner_output.status == TestrunStatus.Completed:
			# Have valid JSON from testrunner. Did it need to get built?
			if self._testrunner_output.parsed["setup"] is not None:
				setup = SubprocessExecutionResult(self._testrunner_output.parsed["setup"])
				if setup.status == ExecutionResult.FailedTimeout:
					self._judge_testcases_without_testbatch(testcases = self._runner, testcase_status = TestcaseStatus.BuildTimedOut)
					return
				elif setup.status != ExecutionResult.Success:
					self._judge_testcases_without_testbatch(testcases = self._runner, testcase_status = TestcaseStatus.BuildFailure)
					return

			# Build either successful or was unnecessary, judge individual testcases.
			for (testbatch_no, testbatch) in enumerate(self._testrunner_output.parsed["testbatches"], 1):
				testbatch_evaluation = TestbatchEvaluation(testbatch, testbatch_no, self._runner)
				if testbatch_evaluation.process.status == ExecutionResult.Success:
					# Process was successful, we have some output. Not sure if it's parsable, yet.
					if testbatch_evaluation.process.have_json_output:
						if not isinstance(testbatch_evaluation.process.stdout_json, dict):
							# Process returned parsable JSON but was not a dict.
							self._judge_testcases_of_testbatch(testbatch_evaluation, TestcaseStatus.BatchFailedInvalidAnswerProvided)
						else:
							# Individual judgement of testcases possible
							responses = testbatch_evaluation.process.stdout_json.get("responses", { })
							for testcase in testbatch_evaluation:
								if testcase.name not in responses:
									testcase_status = TestcaseStatus.NoAnswerProvided
									received_answer = None
								else:
									received_answer = responses[testcase.name]
									testcase_status = TestcaseStatus.Passed if (received_answer == testcase.testcase_answer) else TestcaseStatus.FailedWrongAnswer
								testcase_evaluation = TestcaseEvaluation(testcase = testcase, testbatch_evaluation = testbatch_evaluation, received_answer = received_answer, testcase_status = testcase_status)
								self._evaluated_testcases.append(testcase_evaluation)
					else:
						# Unparsable output.
						self._judge_testcases_of_testbatch(testbatch_evaluation, TestcaseStatus.BatchFailedUnparsableAnswerProvided)
				elif testbatch_evaluation.process.status == ExecutionResult.FailedReturnCode:
					self._judge_testcases_of_testbatch(testbatch_evaluation, TestcaseStatus.BatchFailedReturnCode)
				elif testbatch_evaluation.process.status == ExecutionResult.FailedTimeout:
					self._judge_testcases_of_testbatch(testbatch_evaluation, TestcaseStatus.BatchFailedTimeout)
				elif testbatch_evaluation.process.status == ExecutionResult.FailedExecException:
					self._judge_testcases_of_testbatch(testbatch_evaluation, TestcaseStatus.BatchFailedExecExecption)
				elif testbatch_evaluation.process.status == ExecutionResult.FailedNotExecutable:
					self._judge_testcases_of_testbatch(testbatch_evaluation, TestcaseStatus.BatchFailedNotExecutable)
				elif testbatch_evaluation.process.status == ExecutionResult.FailedOutOfMemory:
					self._judge_testcases_of_testbatch(testbatch_evaluation, TestcaseStatus.BatchFailedOutOfMemory)
				else:
					raise NotImplementedError(f"Unknown process status: {testbatch_evaluation.process.status}")
		else:
			# Docker run failed or produced no JSON, all testcases fail!
			self._judge_testcases_without_testbatch(testcases = self, testcase_status = TestcaseStatus.DockerRunFailed)
			return

	def _get_order_by(self, group_key_fnc: "callable"):
		order = collections.OrderedDict()
		for testcase_evaluation in self._evaluated_testcases:
			key = group_key_fnc(testcase_evaluation)
			if key not in order:
				order[key] = 1
		return list(order.keys())

	def _get_action_order(self):
		return self._get_order_by(lambda testcase_evaluation: testcase_evaluation.testcase.action)

	def _get_collection_order(self):
		return self._get_order_by(lambda testcase_evaluation: testcase_evaluation.testcase.collection_name)

	def _testbatches_to_dict(self):
		result = { }
		for testcase_evaluation in self:
			if testcase_evaluation.testbatch_evaluation.testbatch_no not in result:
				testbatch_no = testcase_evaluation.testbatch_evaluation.testbatch_no
				result[testbatch_no] = {
					"action": testcase_evaluation.testcase.action,
					"status": testcase_evaluation.testbatch_evaluation.process.status.name,
					"runtime_secs": testcase_evaluation.testbatch_evaluation.process.runtime_secs,
					"runtime_allowance_secs": testcase_evaluation.testcase.runtime_allowance_secs,
					"runtime_allowance_secs_unscaled": testcase_evaluation.testcase.runtime_allowance_secs_unscaled,
					"testcase_count": 1,
				}
				if testcase_evaluation.testbatch_evaluation.process.status != ExecutionResult.Success:
					result[testbatch_no]["process"] = testcase_evaluation.testbatch_evaluation.process.to_dict()
			else:
				result[testbatch_no]["runtime_allowance_secs"] += testcase_evaluation.testcase.runtime_allowance_secs
				result[testbatch_no]["runtime_allowance_secs_unscaled"] += testcase_evaluation.testcase.runtime_allowance_secs_unscaled
				result[testbatch_no]["testcase_count"] += 1
		return result

	def to_dict(self):
		return {
			"dut": self._submission.to_dict(),
			"setup": None if (self._testrunner_output.status != TestrunStatus.Completed) else self._testrunner_output.parsed["setup"],
			"action_order": self._get_action_order(),
			"collection_order": self._get_collection_order(),
			"testcases": [ testcase.to_dict() for testcase in self._evaluated_testcases ],
			"testbatches": self._testbatches_to_dict(),
			"statistics_by_action": Statistics(self, group_key_fnc = lambda testcase_evaluation: testcase_evaluation.testcase.action).to_dict(),
			"statistics_by_collection": Statistics(self, group_key_fnc = lambda testcase_evaluation: testcase_evaluation.testcase.collection_name).to_dict(),
			"runner": {
				"kartfire": kartfire.VERSION,
				"container_environment": self._runner.container_environment,
			},
		}

	def __iter__(self):
		return iter(self._evaluated_testcases)

	def __repr__(self):
		return f"SubmissionEvaluation<{str(self.to_dict())}>"
