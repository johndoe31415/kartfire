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
import datetime
import sys
from .TestFixtureConfig import TestFixtureConfig
from .TestcaseRunner import TestcaseRunner
from .TestcaseCollection import TestcaseCollection
from .StateFile import StateFile
from .Submission import Submission
from .BaseAction import BaseAction

class ActionRun(BaseAction):
	def _get_submission_directories(self):
		directories = [ path_name for path_name in self._args.submission_dir if os.path.isdir(path_name) ]
		if self._args.state_file is not None:
			state_file = StateFile(self._args.state_file)
			directories = [ directory for directory in directories if state_file.need_to_run(directory) ]
			state_file.write()
		return directories


	def run(self):
		test_fixture_config = TestFixtureConfig.load_from_file(self._args.test_fixture_config)
		if self._args.interactive:
			test_fixture_config.interactive = True

		testcase_collections = [ TestcaseCollection.load_from_file(tc_filename, test_fixture_config) for tc_filename in self._args.testcase_file ]
		submissions = [ Submission(submission_dir) for submission_dir in self._get_submission_directories() ]
		if len(submissions) == 0:
			print("Nothing to do, no submissions found.", file = sys.stderr)
			return 1

		tcr = TestcaseRunner(testcase_collections = testcase_collections, test_fixture_config = test_fixture_config)
		submission_evaluations = tcr.run(submissions)

		if self._args.output_file is not None:
			outfile = self._args.output_file
		else:
			outfile = f"testrun_{datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}.json"

		with open(outfile, "w") as f:
			result_file = {
				"meta": {
					"type": "testcase_results",
					"created_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
				},
				"content": [ submission_evaluation.to_dict() for submission_evaluation in submission_evaluations ],
			}
			json.dump(result_file, f)
