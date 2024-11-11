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

from .BaseAction import BaseAction
from .ResultPrinter import ResultPrinter

class ActionPrint(BaseAction):
	def _show_submission(self, submission_result: "SubmissionResultPrinter"):
		def matches(search_term):
			return search_term.lower() in submission_result.repo_name.lower()
		return all(matches(search_term) for search_term in self._args.search)

	def run(self):
		result_printer = ResultPrinter.from_file(self._args.testrun_filename, show_only_failed = self._args.verbose < 4, show_results_by_collection = self._args.verbose >= 1, show_results_by_action = self._args.verbose >= 3, show_failed_testcases = self._args.verbose >= 2, show_max_testcase_details_count = self._args.max_failed_testcase_count)
		for submission_result in result_printer.submission_results:
			if self._show_submission(submission_result):
				submission_result.print()
		return 0
