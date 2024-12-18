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

from .TestFixtureConfig import TestFixtureConfig
from .TestcaseRunner import TestcaseRunner
from .TestcaseCollection import TestcaseCollection
from .Submission import Submission
from .BaseAction import BaseAction
from .Enums import TestcaseStatus

class ActionReference(BaseAction):
	def _run_testcase_filename(self, testcase_filename: str):
		test_fixture_config = TestFixtureConfig.load_from_file(self._args.test_fixture_config)
		test_fixture_config.testbatch_maxsize = 1
		testcase_collection = TestcaseCollection.load_from_file(testcase_filename, test_fixture_config)
		reference_submission = Submission(self._args.reference_submission_dir)
		tcr = TestcaseRunner(testcase_collections = [ testcase_collection ], test_fixture_config = test_fixture_config)
		submission_evaluations = tcr.run([ reference_submission ])

		have_answer_cnt = 0
		new_answer_cnt = 0
		evaluation = submission_evaluations[0]

		for testcase_evaluation in evaluation:
			if testcase_evaluation.status not in [ TestcaseStatus.Passed, TestcaseStatus.FailedWrongAnswer ]:
				print(f"{testcase_filename}: Refusing to use a reference with testcase status {testcase_evaluation.status.name}")
				continue

			testcase = testcase_evaluation.testcase
			if testcase.testcase_answer == testcase_evaluation.received_answer:
				have_answer_cnt += 1
			else:
				new_answer_cnt += 1

		total_answer_cnt = have_answer_cnt + new_answer_cnt
		print(f"{testcase_filename}: Already had correct answer for {have_answer_cnt} / {total_answer_cnt} testcases, found {new_answer_cnt} new.")

		if self._args.commit:
			for testcase_evaluation in evaluation:
				testcase = testcase_evaluation.testcase
				if testcase.testcase_answer != testcase_evaluation.received_answer:
					testcase.testcase_answer = testcase_evaluation.received_answer
				testcase.runtime_allowance_secs_unscaled = testcase_evaluation.testbatch_evaluation.process.runtime_secs
				print(f"{testcase.name}: {testcase_evaluation.testbatch_evaluation.process.runtime_secs:.1f} sec")
			testcase_collection.write_to_file(testcase_filename)
		else:
			print(f"{testcase_filename}: Not commiting results.")

	def run(self):
		for testcase_filename in self._args.testcase_filename:
			self._run_testcase_filename(testcase_filename)
