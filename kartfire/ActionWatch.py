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

import os
import asyncio
import time
import traceback
import mailcoil
from .ResultPrinter import ResultPrinter
from .RunResult import MultiRunResult
from .ResultHTMLGenerator import ResultHTMLGenerator
from .CmdlineAction import CmdlineAction
from .Submission import Submission
from .TestRunner import TestRunner
from .AsyncWorkerPool import AsyncWorkerPool

class ActionWatch(CmdlineAction):
	def _load_submissions(self):
		for submission_dir in self._args.submission_dir:
			if os.path.isdir(submission_dir):
				yield Submission(submission_dir, self._test_fixture_config)

	def _print_exception(self, exception):
		print("Git update failed with exception for worker thread:")
		traceback.print_exception(type(exception), exception, exception.__traceback__)

	async def _main_loop(self):
		worker_pool = AsyncWorkerPool(self._test_runner.concurrent_process_count)
		while True:
			submissions = list(self._load_submissions())

			# Filter out all submissions that are currently not Git version controlled
			submissions = [ submission for submission in submissions if submission.git_commit is not None ]

			# Trigger parallel git update for all repositories
			async with AsyncWorkerPool(8, exception_callback = self._print_exception) as pool:
				for submission in submissions:
					pool.submit(submission.update_git())

			if pool.exception_count > 0:
				print(f"Update of submission repositories failed in {pool.exception_count} case(es), delaying and retrying.")
				await asyncio.sleep(10)
				continue

			# Retrieve latest run metadata
			latest_metadata = { row["source"]: row["source_metadata"] for row in self._db.get_most_recent_multirun_by_source() }

			# Filter out all submissions for which we have tested this exact git commit already
			submissions = [ submission for submission in submissions if submission.git_commit != latest_metadata.get(submission.shortname, { }).get("meta", { }).get("git", { }).get("commit") ]

			print(f"Repository watcher has currently {worker_pool.slots_free} open slots, requested run of {len(submissions)} solutions.")

			# Prioritize solutions by time spent in pipeline (those which use
			# more CPU previously are less likely to get in)
			time_spent_in_pipeline = self._db.get_time_spent_in_pipeline()
			submissions.sort(key = lambda submission: time_spent_in_pipeline.get(submission.shortname, 0))

			wait_end_time = time.monotonic() + self._args.loop_duration
			while True:
				if time.monotonic() > wait_end_time:
					break

				while (worker_pool.slots_free > 0) and (len(submissions) > 0):
					next_submission = submissions.pop(0)
					print(f"Submitting for testing: {next_submission}")
					worker_pool.submit(self._test_runner.run_submission(next_submission))

				await asyncio.sleep(1)

			if len(submissions) > 0:
				print(f"{len(submissions)} submissions still pending after validation cycle, currently {worker_pool.slots_free} slots free and {worker_pool.pending} tasks pending.")
			else:
				print("All submissions were run in this cycle.")


	def _multirun_finished_callback(self, submission: Submission, multirun_id: int):
		print(f"Finished testing submission: {submission}")
		multirun_result = MultiRunResult(self._db, multirun_id)
#		self._rp.multirun.print_details(multirun_result)
		if self._dropoff is not None:
			multirun_result.send_email(test_fixture_config = self._test_fixture_config, html_generator = self._html_generator, dropoff = self._dropoff)

	def run(self):
		if self._args.send_email:
			self._dropoff = mailcoil.MailDropoff.parse_uri(self._test_fixture_config.email_via_uri)
			self._html_generator = ResultHTMLGenerator(self._db)
		else:
			self._dropoff = None

		self._rp = ResultPrinter(self._db)

		collection_names = self._args.collection_name.split(",")
		tc_collections = [ self._db.get_testcase_collection(collection_name) for collection_name in collection_names ]
		self._test_runner = TestRunner(tc_collections, self._test_fixture_config, self._db)
		self._test_runner.register_multirun_finished_callback(self._multirun_finished_callback)
		asyncio.run(self._main_loop())
