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
import enum
import collections
from .Enums import TestcaseStatus

class StatisticsPrinter(enum.Enum):
	ShowAllStats = "all"
	ShowOnlyFailed = "onlyfailed"

class ResultPrinter():
	def __init__(self, results: dict, include_which_stats: StatisticsPrinter = StatisticsPrinter.ShowAllStats):
		self._results = results
		self._include_which_stats = include_which_stats
		self._results_by_repo = { }
		for solution in self._results["content"]:
			self._results_by_repo[solution["dut"]["dirname"]] = solution

	def print_result(self, repo_name: str):
		solution = self._results_by_repo[repo_name]
		basename = os.path.basename(repo_name)
		print(f"{basename}: {solution['statistics_by_action']['*']['passed']} / {solution['statistics_by_action']['*']['total']} {100 * solution['statistics_by_action']['*']['passed'] / solution['statistics_by_action']['*']['total']:.1f}%")

	def print_statistics(self, statistics: dict, order: list):
		for item in order:
			stats = statistics[item]

			match self._include_which_stats:
				case StatisticsPrinter.ShowAllStats:
					show_this = True

				case StatisticsPrinter.ShowOnlyFailed:
					show_this = stats["failed"] > 0

			if show_this:
				print(f"    {item}: {stats['passed']} / {stats['total']} {100 * stats['passed'] / stats['total']:.1f}%")

	def print_result_by_collection(self, repo_name: str):
		solution = self._results_by_repo[repo_name]
		self.print_statistics(solution["statistics_by_collection"], order = solution["collection_order"])

	def print_failed_testcases(self, repo_name: str):
		failed_keys = collections.Counter()
		solution = self._results_by_repo[repo_name]
		for testbatch in solution["testbatches"]:
			for testcase in testbatch["testcases"]:
				status = getattr(TestcaseStatus, testcase["testcase_status"])
				if status == TestcaseStatus.Passed:
					pass
				else:
					action = testcase["definition"]["testcase_data"]["action"]
					key = (action, status)
					failed_keys[key] += 1
					if failed_keys[key] <= 1:
						print(f"    Testcase {testcase['definition']['name']} failed with status {status.name}")
						if status == TestcaseStatus.FailedWrongAnswer:
							print("Testcase:")
							print(json.dumps(testcase["definition"]["testcase_data"], indent = "\t"))
							print()
							print("Expected answer:")
							print(json.dumps(testcase["definition"]["testcase_answer"], indent = "\t"))
							print()
							print("Received answer:")
							print(json.dumps(testcase["received_answer"], indent = "\t"))
							print()
						#passelif status == TestcaseStatus.FailedWrongAnswer:

	def print(self):
		for repo_name in sorted(self._results_by_repo):
			self.print_result(repo_name)
			self.print_result_by_collection(repo_name)
			self.print_failed_testcases(repo_name)
			print()

	@classmethod
	def from_file(cls, json_filename: str, include_which_stats: StatisticsPrinter = StatisticsPrinter.ShowAllStats):
		with open(json_filename) as f:
			return cls(results = json.load(f), include_which_stats = include_which_stats)
