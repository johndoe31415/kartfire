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
from .TestRunner import TestRunner
from .Submission import Submission
from .ResultPrinter import ResultPrinter
from .RunResult import MultiRunResult

class ActionRun(CmdlineAction):
	def _build_finished_callback(self, multirun_id: int):
		multirun_result = MultiRunResult(self._db, multirun_id)
		if multirun_result.build_failed:
			self._rp.print_multirun_overview(multirun_result)

	def _run_finished_callback(self, submission: Submission, run_id: int):
		run_result = MultiRunResult.load_single_run(self._db, run_id)
		self._rp.print_run_overview(run_result)

	def _multirun_finished_callback(self, submission: Submission, run_ids: list[int]):
		self._run_ids.append((submission, run_ids))

	def run(self):
		self._run_ids = [ ]
		self._rp = ResultPrinter(self._db)
		collection_names = self._args.collection_name.split(",")
		tc_collections = [ self._db.get_testcase_collection(collection_name) for collection_name in collection_names ]
		runner = TestRunner(tc_collections, self._test_fixture_config, self._db, interactive = self._args.interactive)
		runner.register_build_finished_callback(self._build_finished_callback)
		runner.register_run_finished_callback(self._run_finished_callback)
		runner.register_multirun_finished_callback(self._multirun_finished_callback)
		ignored_count = 0
		submissions = [ ]
		for submission_dir in self._args.submission_dir:
			if os.path.isdir(submission_dir):
				submissions.append(Submission(submission_dir, self._test_fixture_config))
			else:
				ignored_count += 1
		if ignored_count == 1:
			print(f"{ignored_count} argument was ignored because it was no directory.", file = sys.stderr)
		elif ignored_count > 1:
			print(f"{ignored_count} arguments were ignored because they were no directories.", file = sys.stderr)
		if len(submissions) == 0:
			print("No submissions to test found.", file = sys.stderr)
		runner.run(submissions)

		print("=" * 120)
#		for (submission, run_ids) in sorted(self._run_ids, key = lambda entry: (entry[0].shortname, entry[1])):
#			for run_id in run_ids:
#				self._rp.print_overview(run_id)
