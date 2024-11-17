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
from .TestbatchEvaluation import TestbatchEvaluation
from .Enums import TestrunStatus, TestcaseStatus

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
		for testbatch_evaluation in self._submission_evaluation.testbatch_evaluations:
			for testcase_evaluation in testbatch_evaluation:
				key = self._group_key_fnc(testcase_evaluation)
				self._account_statistic_of(key = "*", testcase_evaluation = testcase_evaluation)
				self._account_statistic_of(key = key, testcase_evaluation = testcase_evaluation)

	def to_dict(self) -> dict:
		return self._statistics

class SubmissionEvaluation():
	def __init__(self, testrunner_output: "TestrunnerOutput", runner: "TestcaseRunner", submission: "Submission"):
		self._testrunner_output = testrunner_output
		self._runner = runner
		self._submission = submission

	@property
	def testrun_status(self):
		return self._testrunner_output.status

	@functools.cached_property
	def testcase_count(self):
		# TODO anders
		return sum(testbatch_evaluation.testcase_count for testbatch_evaluation in self.testbatch_evaluations)

	@functools.cached_property
	def passed_testcase_count(self):
		return sum(testbatch_evaluation.passed_testcase_count for testbatch_evaluation in self.testbatch_evaluations)

	@property
	def failed_testcase_count(self):
		return self.testcase_count - self.passed_testcase_count

	@property
	def testbatch_evaluations(self):
		if self._testrunner_output.status == TestrunStatus.Completed:
			for testbatch_result in self._testrunner_output.parsed["testbatches"]:
				yield TestbatchEvaluation(self._runner, testbatch_result)

	def _get_order_by(self, group_key_fnc: "callable"):
		order = collections.OrderedDict()
		for testbatch_evaluation in self.testbatch_evaluations:
			for testcase_evaluation in testbatch_evaluation:
				key = group_key_fnc(testcase_evaluation)
				if key not in order:
					order[key] = 1
		return list(order.keys())

	def _get_action_order(self):
		return self._get_order_by(lambda testcase_evaluation: testcase_evaluation.testcase.action)

	def _get_collection_order(self):
		return self._get_order_by(lambda testcase_evaluation: testcase_evaluation.testcase.collection_name)

	def to_dict(self):
		print(self._testrunner_output.status)
		return {
			"dut": self._submission.to_dict(),
			"setup": None if (self._testrunner_output.status != TestrunStatus.Completed) else self._testrunner_output.parsed["setup"],
			"testrun_status": self.testrun_status.name,
			"action_order": self._get_action_order(),
			"collection_order": self._get_collection_order(),
			"testbatches": [ testbatch_eval.to_dict() for testbatch_eval in self.testbatch_evaluations ],
			"statistics_by_action": Statistics(self, group_key_fnc = lambda testcase_evaluation: testcase_evaluation.testcase.action).to_dict(),
			"statistics_by_collection": Statistics(self, group_key_fnc = lambda testcase_evaluation: testcase_evaluation.testcase.collection_name).to_dict(),
			"runner": {
				"kartfire": kartfire.VERSION,
				"container_environment": self._runner.container_environment,
			},
		}

	def __repr__(self):
		return f"SubmissionEvaluation<{str(self.to_dict())}>"
