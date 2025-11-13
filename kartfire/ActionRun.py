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
import mailcoil
from .CmdlineAction import CmdlineAction
from .TestRunner import TestRunner
from .Submission import Submission
from .ResultPrinter import ResultPrinter
from .RunResult import MultiRunResult
from .ResultHTMLGenerator import ResultHTMLGenerator

class ActionRun(CmdlineAction):
	def _build_finished_callback(self, multirun_id: int):
		multirun_result = MultiRunResult(self._db, multirun_id)
		if multirun_result.build_failed:
			self._rp.print_multirun_overview(multirun_result)

	def _run_finished_callback(self, submission: Submission, run_id: int):
		run_result = MultiRunResult.load_single_run(self._db, run_id)
		self._rp.print_run_overview(run_result)

	def _multirun_finished_callback(self, submission: Submission, multirun_id: int):
		multirun_result = MultiRunResult(self._db, multirun_id)
		self._multiruns.append(multirun_result)
		if self._dropoff is not None:
			multirun_result.send_email(test_fixture_config = self._test_fixture_config, html_generator = self._html_generator, dropoff = self._dropoff)

	def run(self):
		if self._args.send_email:
			self._dropoff = mailcoil.MailDropoff.parse_uri(self._test_fixture_config.email_via_uri)
			self._html_generator = ResultHTMLGenerator(self._db)
		else:
			self._dropoff = None

		self._multiruns = [ ]
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

		print("═" * 120)
		self._rp.print_table(sorted(self._multiruns, key = lambda multirun: (multirun.shortname, multirun.multirun_id)))
