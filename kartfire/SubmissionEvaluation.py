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
from .TestbatchEvaluation import TestbatchEvaluation
from .Enums import TestrunStatus, TestcaseStatus

class SubmissionEvaluation():
	def __init__(self, testrunner_output: "TestrunnerOutput", runner: "TestcaseRunner", submission: "Submission"):
		self._testrunner_output = testrunner_output
		self._runner = runner
		self._submission = submission
		self._statistics = { }
		self._compute_statistics()

	@property
	def testrun_status(self):
		return self._testrunner_output.status

	@functools.cached_property
	def testcase_count(self):
		return sum(testbatch_evaluation.testcase_count for testbatch_evaluation in self.testbatch_evaluation)

	@functools.cached_property
	def passed_testcase_count(self):
		return sum(testbatch_evaluation.passed_testcase_count for testbatch_evaluation in self.testbatch_evaluation)

	@property
	def failed_testcase_count(self):
		return self.testcase_count - self.passed_testcase_count

	@property
	def testbatch_evaluation(self):
		if self._testrunner_output.status == TestrunStatus.Completed:
			for testbatch_results in self._testrunner_output:
				yield TestbatchEvaluation(self._runner, testbatch_results)

	def _account_statistic_of(self, action: str, testcase_evaluation: "TestcaseEvaluation"):
		if action not in self._statistics:
			self._statistics[action] = {
				"total": 0,
				"passed": 0,
				"failed": 0,
				"breakdown": collections.Counter(),
			}
		self._statistics[action]["total"] += 1
		if testcase_evaluation.status == TestcaseStatus.Passed:
			self._statistics[action]["passed"] += 1
		else:
			self._statistics[action]["failed"] += 1
		self._statistics[action]["breakdown"][testcase_evaluation.status.name] += 1

	def _compute_statistics(self):
		for testbatch_evaluations in self.testbatch_evaluation:
			for testcase_evaluation in testbatch_evaluations:
				self._account_statistic_of(action = "*", testcase_evaluation = testcase_evaluation)
				self._account_statistic_of(action = testcase_evaluation.testcase.action, testcase_evaluation = testcase_evaluation)

	def _get_action_order(self):
		order = collections.OrderedDict()
		for testbatch_evaluation in self.testbatch_evaluation:
			for testcase in testbatch_evaluation:
				if testcase.testcase.action not in order:
					order[testcase.testcase.action] = 1
		return list(order.keys())

	def to_dict(self):
		return {
			"dut": self._submission.to_dict(),
			"testrun_status": self.testrun_status.name,
			"action_order": self._get_action_order(),
			"testbatches": [ testbatch_eval.to_dict() for testbatch_eval in self.testbatch_evaluation ],
			"statistics": self._statistics,
		}

	def __repr__(self):
		return f"SubmissionEvaluation<{str(self.to_dict())}>"
