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
import collections
import datetime
import pytz
import tzlocal
from .Enums import TestcaseStatus
from .TimeDelta import TimeDelta

class SubmissionResultPrinter():
	def __init__(self, result_printer: "ResultPrinter", submission_results: dict):
		self._result_printer = result_printer
		self._submission_results = submission_results

	@property
	def repo_dir(self):
		return self._submission_results["dut"]["dirname"]

	@property
	def repo_basename(self):
		return os.path.basename(self.repo_dir)

	@property
	def repo_name(self):
		if self.submission_owner is None:
			return self.repo_basename
		else:
			return f"{self.repo_basename} / {self.submission_owner}"

	@property
	def submission_owner(self):
		if "kartfire" in self._submission_results["dut"]["meta"]["json"]:
			return self._submission_results['dut']['meta']['json']['kartfire']['name']
		else:
			return None

	def _print_timezone(self):
		name = tzlocal.get_localzone().key
		return pytz.timezone(name)

	@property
	def git_text(self):
		if "git" in self._submission_results["dut"]["meta"]:
			commit = self._submission_results["dut"]["meta"]["git"]["commit"][:8]
			commit_date = self._submission_results["dut"]["meta"]["git"]["date"]
			commit_ts = datetime.datetime.strptime(commit_date, "%Y-%m-%d %H:%M:%S %z")
			print_timezone = self._print_timezone()
			commit_ts_utc = datetime.datetime.fromtimestamp(commit_ts.timestamp())
			commit_ts_local = print_timezone.localize(commit_ts_utc)
			time_delta = TimeDelta((commit_ts_utc - datetime.datetime.utcnow()).total_seconds())
			return f"{commit} {commit_ts_local.strftime('%a, %Y-%m-%d %H:%M')} {time_delta}"
		else:
			return "-"

	def print_result(self):
		if "*" in self._submission_results["statistics_by_action"]:
			print(f"{self.repo_name} {self.git_text}: {self._submission_results['statistics_by_action']['*']['passed']} / {self._submission_results['statistics_by_action']['*']['total']} {100 * self._submission_results['statistics_by_action']['*']['passed'] / self._submission_results['statistics_by_action']['*']['total']:.1f}%")
		else:
			print(f"{self.repo_name} {self.git_text}: no data available")

	def print_statistics(self, statistics: dict, order: list):
		for item in order:
			stats = statistics[item]
			if self._result_printer.show_only_failed:
				show_this = stats["failed"] > 0
			else:
				show_this = True

			if show_this:
				print(f"    {item}: {stats['passed']} / {stats['total']} {100 * stats['passed'] / stats['total']:.1f}%")

	def print_result_by_collection(self):
		self.print_statistics(self._submission_results["statistics_by_collection"], order = self._submission_results["collection_order"])

	def print_failed_testcases(self):
		failed_keys = collections.Counter()
		for testbatch in self._submission_results["testbatches"]:
			for testcase in testbatch["testcases"]:
				status = getattr(TestcaseStatus, testcase["testcase_status"])
				if status == TestcaseStatus.Passed:
					pass
				else:
					action = testcase["definition"]["testcase_data"]["action"]
					key = (action, status)
					failed_keys[key] += 1
					first_failed_key = failed_keys[key] == 1
					print_specific_key = (status == TestcaseStatus.FailedWrongAnswer) and (failed_keys[key] <= self._result_printer.show_max_testcase_details_count)
					if first_failed_key or print_specific_key:
						print(f"    Testcase {testcase['definition']['name']} failed with status {status.name}")
						if print_specific_key:
							print(json.dumps(testcase["definition"]["testcase_data"], indent = "\t"))
							print()
							print("Expected answer:")
							print(json.dumps(testcase["definition"]["testcase_answer"], indent = "\t"))
							print()
							print("Received answer:")
							print(json.dumps(testcase["received_answer"], indent = "\t"))
							print()
							print("-" * 120)
						#passelif status == TestcaseStatus.FailedWrongAnswer:

	def print(self):
		self.print_result()
		self.print_result_by_collection()
		self.print_failed_testcases()
		print()


class ResultPrinter():
	def __init__(self, results: dict, show_only_failed: bool = True, show_results_by_collection: bool = True, show_results_by_action: bool = False, show_failed_testcases: bool = True, show_max_testcase_details_count: int = 0):
		self._results = results
		self._show_only_failed = show_only_failed
		self._show_results_by_collection = show_results_by_collection
		self._show_results_by_action = show_results_by_action
		self._show_failed_testcases = show_failed_testcases
		self._show_max_testcase_details_count = show_max_testcase_details_count
		self._results_by_repo_dir = { }
		for solution in self._results["content"]:
			self._results_by_repo_dir[solution["dut"]["dirname"]] = solution

	@property
	def show_only_failed(self):
		return self._show_only_failed

	@property
	def show_results_by_collection(self):
		return self._show_results_by_collection

	@property
	def show_results_by_action(self):
		return self._show_results_by_action

	@property
	def show_failed_testcases(self):
		return self._show_failed_testcases

	@property
	def show_max_testcase_details_count(self):
		return self._show_max_testcase_details_count

	@property
	def submission_results(self):
		for repo_dir in sorted(self._results_by_repo_dir):
			submission_results = self._results_by_repo_dir[repo_dir]
			yield SubmissionResultPrinter(self, submission_results)

	@classmethod
	def from_file(cls, json_filename: str, **kwargs):
		with open(json_filename) as f:
			return cls(results = json.load(f), **kwargs)
