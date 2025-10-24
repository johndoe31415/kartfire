#	kartfire - Test framework to consistently run submission files
#	Copyright (C) 2023-2025 Johannes Bauer
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

import sys
import os
from .CmdlineAction import CmdlineAction
from .TestcaseRunner import TestcaseRunner
from .Submission import Submission
from .ResultPrinter import ResultPrinter

class ActionRun(CmdlineAction):
	def run(self):
		tc_collection = self._db.get_testcase_collection(self._args.collection_name)
		runner = TestcaseRunner(tc_collection, self._test_fixture_config, self._db, interactive = self._args.interactive)
		ignored_count = 0
		submissions = [ ]
		for submission_dir in self._args.submission_dir:
			if os.path.isdir(submission_dir):
				submissions.append(Submission(submission_dir))
			else:
				ignored_count += 1
		if ignored_count == 1:
			print(f"{ignored_count} argument was ignored because it was no directory.", file = sys.stderr)
		elif ignored_count > 1:
			print(f"{ignored_count} arguments were ignored because they were no directories.", file = sys.stderr)
		if len(submissions) == 0:
			print("No submissions to test found.", file = sys.stderr)
		run_ids = runner.run(submissions)

		rp = ResultPrinter(self._db)
		for run_id in run_ids:
			rp.print_overview(run_id)
