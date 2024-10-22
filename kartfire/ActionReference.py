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

import os
import json
import logging
import collections
from .TestFixtureConfig import TestFixtureConfig
from .TestcaseRunner import TestcaseRunner
from .TestcaseCollection import TestcaseCollection
from .Submission import Submission
from .BaseAction import BaseAction

class ActionReference(BaseAction):
	def run(self):
		test_fixture_config = TestFixtureConfig.load_from_file(self._args.test_fixture_config)
		testcase_collection = TestcaseCollection.load_from_file(self._args.testcase_filename, test_fixture_config)
		reference_submission = Submission(self._args.reference_submission_dir)
		tcr = TestcaseRunner(testcase_collections = [ testcase_collection ], test_fixture_config = test_fixture_config)
		submission_evaluations = tcr.run([ reference_submission ])

		have_answer_cnt = 0
		new_answer_cnt = 0
		evaluation = submission_evaluations[0]
		for testbatch_evaluation in evaluation.testbatch_evaluation:
			for testcase_evaluation in testbatch_evaluation:
				testcase = testcase_evaluation.testcase
				if testcase.testcase_answer == testcase_evaluation.received_answer:
					have_answer_cnt += 1
				else:
					new_answer_cnt += 1

		total_answer_cnt = have_answer_cnt + new_answer_cnt
		print(f"Already had correct answer for {have_answer_cnt} / {total_answer_cnt} testcases, found {new_answer_cnt} new.")

		if new_answer_cnt == 0:
			print("No new test case answers to add.")
		else:
			if self._args.commit:
				for testbatch_evaluation in evaluation.testbatch_evaluation:
					for testcase_evaluation in testbatch_evaluation:
						testcase = testcase_evaluation.testcase
						if testcase.testcase_answer != testcase_evaluation.received_answer:
							testcase.testcase_answer = testcase_evaluation.received_answer


				testcase_collection.write_to_file(self._args.testcase_filename)
			else:
				print(f"Not commiting results to {self._args.testcase_filename}.")
