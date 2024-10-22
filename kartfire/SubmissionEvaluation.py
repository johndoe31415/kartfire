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
	def testrun_status(self):
		return self._testrunner_output.status

	@property
	def testcase_count(self):
		return sum(testbatch_evaluation.testcase_count for testbatch_evaluation in self.testbatch_evaluation)

	@property
	def testbatch_evaluation(self):
		if self._testrunner_output.status == TestrunStatus.Completed:
			for testbatch_results in self._testrunner_output:
				yield TestbatchEvaluation(self._runner, testbatch_results)

	def _compute_breakdowns(self):
		breakdown = collections.Counter()
		for testbatch_evaluation in self.testbatch_evaluation:
			for testcase in testbatch_evaluation:
				breakdown[testcase.status] += 1
		breakdown = { enumitem.name: value for (enumitem, value) in breakdown.items() }
		return breakdown

	def to_dict(self):
		return {
			"dut": self._submission.to_dict(),
			"testrun_status": self.testrun_status.name,
			"testcase_count_total": self.testcase_count,
			"testbatches": [ testbatch_eval.to_dict() for testbatch_eval in self.testbatch_evaluation ],
			"breakdown": self._compute_breakdowns(),
		}

	def __repr__(self):
		return f"SubmissionEvaluation<{str(self.to_dict())}>"
