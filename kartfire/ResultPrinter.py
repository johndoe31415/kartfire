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

class ResultColorizer():
	def __init__(self, ansi: bool = True):
		self._ansi = ansi

	@property
	def clr(self):
		return "\x1b[0m" if self._ansi else ""

	@property
	def red(self):
		return "\x1b[31m" if self._ansi else ""

	@property
	def green(self):
		return "\x1b[32m" if self._ansi else ""

	@property
	def yellow(self):
		return "\x1b[33m" if self._ansi else ""

	def ratio(self, ratio: float):
		if ratio < 0:
			ratio = 0
		elif ratio > 1:
			ratio = 1
		if ratio < 0.66:
			return self.red
		elif ratio < 1:
			return self.yellow
		else:
			return self.green

class SubmissionResultPrinter():
	def __init__(self, result_printer: "ResultPrinter", submission_results: dict):
		self._result_printer = result_printer
		self._submission_results = submission_results

	@property
	def col(self):
		return self._result_printer.colorizer

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
		if "kartfire" in self._submission_results["dut"]["meta"].get("json", { }):
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

	def _ratio_by_collection(self):
		passed = 0
		total_cnt = len(self._submission_results["statistics_by_collection"]) - 1
		for (name, stats) in self._submission_results["statistics_by_collection"].items():
			if name == "*":
				continue
			if stats["passed"] == stats["total"]:
				passed += 1
		if total_cnt > 0:
			return (passed, total_cnt, passed / total_cnt)
		else:
			return (0, 0, 0)

	def print_result(self):
		if "*" in self._submission_results["statistics_by_action"]:
			ratio = self._submission_results["statistics_by_action"]["*"]["passed"] / self._submission_results["statistics_by_action"]["*"]["total"]
			(collection_pass, collection_total, collection_ratio) = self._ratio_by_collection()
			print(f"{self.repo_name} {self.git_text}: {self.col.ratio(ratio)}{self._submission_results['statistics_by_action']['*']['passed']} / {self._submission_results['statistics_by_action']['*']['total']} {100 * ratio:.1f}%{self.col.clr}, {self.col.ratio(collection_ratio)}{collection_pass} / {collection_total} collections ({collection_ratio * 100:.1f}%){self.col.clr}")
		else:
			print(f"{self.repo_name} {self.git_text}: {self.col.red}no data available{self.col.clr}")

	def print_statistics(self, statistics: dict, order: list, prefix: str):
		for item in order:
			stats = statistics[item]
			if self._result_printer.show_only_failed:
				show_this = stats["failed"] > 0
			else:
				show_this = True

			if show_this:
				ratio = stats["passed"] / stats["total"]
				print(f"    {prefix} {item}: {self.col.ratio(ratio)}{stats['passed']} / {stats['total']} {100 * ratio:.1f}%{self.col.clr}")

	def print_result_by_collection(self):
		self.print_statistics(self._submission_results["statistics_by_collection"], order = self._submission_results["collection_order"], prefix = "Collection")

	def print_result_by_action(self):
		self.print_statistics(self._submission_results["statistics_by_action"], order = self._submission_results["action_order"], prefix = "Action")

	def _print_output(self, output_name: str, output_data: str, show_if_empty: bool = False):
		output_data = output_data.decode("utf-8", errors = "replace").strip("\r\n")
		if output_data != "":
			print(f"{output_name}:")
			print(output_data)
			print()
			print()
		elif show_if_empty:
			print(f"No {output_name} output generated.")

	def print_failed_testcases(self):
		failed_keys = collections.Counter()
#		for testbatch in self._submission_results["testbatches"]:
#			testbatch_status = getattr(TestbatchStatus, testbatch["testbatch_status"])
#			process = SubprocessExecutionResult(testbatch["process"])
		for testcase in self._submission_results["testcases"]:
			testcase_status = getattr(TestcaseStatus, testcase["testcase_status"])
			if testcase_status == TestcaseStatus.Passed:
				pass
			else:
				action = testcase["definition"]["testcase_data"]["action"]
				key = (action, testcase_status)
				failed_keys[key] += 1
				first_failed_key = failed_keys[key] == 1
				print_specific_key =  failed_keys[key] <= self._result_printer.show_max_testcase_details_count
				if first_failed_key or print_specific_key:
					reasons = [ ]
#						if "proc_details" in testbatch:
#							if ("exception_msg" in testbatch["proc_details"]) and (testbatch["proc_details"]["exception_msg"] is not None):
#								reasons.append(testbatch["proc_details"]["exception_msg"])
#							elif ("returncode" in testbatch["proc_details"]) and (testbatch["proc_details"]["returncode"] >= 0):
#								reasons.append(f"return code {testbatch['proc_details']['returncode']}")
#							try:
#								json.loads(testbatch["proc_details"]["stdout"])
#							except json.decoder.JSONDecodeError:
#								if testbatch["proc_details"]["stdout"].strip("\r\n") == "":
#									reasons.append("no stdout provided")
#								else:
#									reasons.append("invalid JSON on stdout")
					#print(f"    Testcase {testcase['definition']['name']} failed with status {status.name} after {process.runtime_secs:.0f} secs: {', '.join(reasons) if len(reasons) > 0 else ''}")
#						print(key)
#						if print_specific_key:
#							if status == TestcaseStatus.FailedWrongAnswer:
#								print(json.dumps(testcase["definition"]["testcase_data"], indent = "\t"))
#								print()
#								print("Expected answer:")
#								print(json.dumps(testcase["definition"]["testcase_answer"], indent = "\t"))
#								print()
#								print("Received answer:")
#								print(json.dumps(testcase["received_answer"], indent = "\t"))
#								print()
#								print("-" * 120)
#							elif status == TestcaseStatus.TestbatchFailedError:
#								self._print_output("stdout", process.stdout, show_if_empty = False)
#								self._print_output("stderr", process.stderr, show_if_empty = False)

	def print(self):
		self.print_result()
		if self._result_printer.show_results_by_collection:
			self.print_result_by_collection()
		if self._result_printer.show_results_by_action:
			self.print_result_by_action()
		if self._result_printer.show_failed_testcases:
			self.print_failed_testcases()
		if self._result_printer.show_results_by_collection or self._result_printer.show_results_by_action or self._result_printer.show_failed_testcases:
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
		self._colorizer = ResultColorizer()

	@property
	def colorizer(self):
		return self._colorizer

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

	def print_all(self):
		for submission_result in self.submission_results:
			submission_result.print()

	@classmethod
	def from_file(cls, json_filename: str, **kwargs):
		with open(json_filename) as f:
			return cls(results = json.load(f), **kwargs)
