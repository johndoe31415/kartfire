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
from .TestbatchEvaluation import TestbatchEvaluation
from .Enums import TestrunStatus

class SubmissionEvaluation():
	def __init__(self, testrunner_output: "TestrunnerOutput", runner: "TestcaseRunner", submission: "Submission"):
		self._testrunner_output = testrunner_output
		self._runner = runner
		self._submission = submission

	@property
	def testcase_count(self):
		if (self._testrunner_output.status == TestrunStatus.Completed) and (self._testrunner_output.testcase_count == self._runner.testcase_count):
			return self._testrunner_output.testcase_count
		else:
			return 0

	@property
	def testbatch_evaluation(self):
		if self._testrunner_output.status == TestrunStatus.Completed:
			for testbatch_results in self._testrunner_output:
				yield TestbatchEvaluation(self._runner, testbatch_results)

	def _compute_breakdown(self, testcase_subset):
		ctr = collections.Counter(testcase.status for testcase in testcase_subset)
		testcase_count = sum(ctr.values())
		result = { }
		total_cnt = 0
		for (status, count) in ctr.items():
			total_cnt += count
			result[status.name] = {
				"cnt": count,
				"%": count / testcase_count * 100,
			}
		result["Total"] = total_cnt
		return result

	def _compute_breakdowns(self):
		result = {
			"*": self._compute_breakdown(self.testbatch_evaluation),
		}
		for action in self._runner.actions:
			result[action] = self._compute_breakdown(testcase_eval for testcase_eval in self.testbatch_evaluation if testcase_eval.testcase.action == action)
		print(result)
		return result

	def to_dict(self):
		return {
			"dut": self._submission.to_dict(),
			"status": self._testrunner_output.status.name,
			"testcase_count_total": self.testcase_count,
			"testbatches": [ testbatch_eval.to_dict() for testbatch_eval in self.testbatch_evaluation ],
#			"breakdown": self._compute_breakdowns(),
		}

	def __repr__(self):
		return str(self.to_dict())
