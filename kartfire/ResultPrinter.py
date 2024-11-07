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
import datetime
import pytz
import tzlocal
from .Enums import TestcaseStatus
from .TimeDelta import TimeDelta

class StatisticsPrinter(enum.Enum):
	ShowAllStats = "all"
	ShowOnlyFailed = "onlyfailed"

class ResultPrinter():
	def __init__(self, results: dict, include_which_stats: StatisticsPrinter = StatisticsPrinter.ShowAllStats, show_max_testcase_data: int = 0):
		self._results = results
		self._include_which_stats = include_which_stats
		self._show_max_testcase_data = show_max_testcase_data
		self._results_by_repo_dir = { }
		for solution in self._results["content"]:
			self._results_by_repo_dir[solution["dut"]["dirname"]] = solution

	def _print_timezone(self):
		name = tzlocal.get_localzone().key
		return pytz.timezone(name)

	def repo_name(self, repo_dir: str):
		basename = os.path.basename(repo_dir)
		solution = self._results_by_repo_dir[repo_dir]
		if "kartfire" in solution["dut"]["meta"]["json"]:
			return f"{basename} / {solution['dut']['meta']['json']['kartfire']['name']}"
		else:
			return basename

	def git_text(self, repo_dir: str):
		basename = os.path.basename(repo_dir)
		solution = self._results_by_repo_dir[repo_dir]
		if "git" in solution["dut"]["meta"]:
			commit = solution["dut"]["meta"]["git"]["commit"][:8]
			commit_date = solution["dut"]["meta"]["git"]["date"]
			commit_ts = datetime.datetime.strptime(commit_date, "%Y-%m-%d %H:%M:%S %z")
			print_timezone = self._print_timezone()
			commit_ts_utc = datetime.datetime.fromtimestamp(commit_ts.timestamp())
			commit_ts_local = print_timezone.localize(commit_ts_utc)
			time_delta = TimeDelta((commit_ts_utc - datetime.datetime.utcnow()).total_seconds())
			return f"{commit} {commit_ts_local.strftime('%a, %Y-%m-%d %H:%M')} {time_delta}"
		else:
			return "-"

	def print_result(self, repo_dir: str):
		solution = self._results_by_repo_dir[repo_dir]
		if "*" in solution["statistics_by_action"]:
			print(f"{self.repo_name(repo_dir)} {self.git_text(repo_dir)}: {solution['statistics_by_action']['*']['passed']} / {solution['statistics_by_action']['*']['total']} {100 * solution['statistics_by_action']['*']['passed'] / solution['statistics_by_action']['*']['total']:.1f}%")
		else:
			print(f"{self.repo_name(repo_dir)} {self.git_text(repo_dir)}: no data available")

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

	def print_result_by_collection(self, repo_dir: str):
		solution = self._results_by_repo_dir[repo_dir]
		self.print_statistics(solution["statistics_by_collection"], order = solution["collection_order"])

	def print_failed_testcases(self, repo_dir: str):
		failed_keys = collections.Counter()
		solution = self._results_by_repo_dir[repo_dir]
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
						if (status == TestcaseStatus.FailedWrongAnswer) and (failed_keys[key] <= self._show_max_testcase_data):
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
		for repo_dir in sorted(self._results_by_repo_dir):
			self.print_result(repo_dir)
			self.print_result_by_collection(repo_dir)
			self.print_failed_testcases(repo_dir)
			print()

	@classmethod
	def from_file(cls, json_filename: str, include_which_stats: StatisticsPrinter = StatisticsPrinter.ShowAllStats):
		with open(json_filename) as f:
			return cls(results = json.load(f), include_which_stats = include_which_stats)
