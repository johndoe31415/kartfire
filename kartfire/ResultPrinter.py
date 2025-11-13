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

import enum
import json
import collections
import datetime
import tzlocal
from .Enums import TestrunStatus, TestresultStatus
from .RunResult import MultiRunResult
from .TableFormatter import Table, CellFormatter

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

	@property
	def blue(self):
		return "\x1b[34m" if self._ansi else ""

	@property
	def purple(self):
		return "\x1b[35m" if self._ansi else ""

	@property
	def cyan(self):
		return "\x1b[36m" if self._ansi else ""

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

class ResultBar():
	def __init__(self, display: tuple, clear_color: str, length: int = 30):
		self._display = display
		self._clear_color = clear_color
		self._length = length

	def __call__(self, run_result: "RunResult"):
		if not run_result.have_results:
			# No tests run?
			return "[" + (" " * self._length) + "]"

		result = { }
		total_chars_used = 0
		for (value, symbol, color) in self._display:
			match_count = run_result.result_count_dict.get(value, 0)
			if match_count > 0:
				char_count = max(1, round(match_count / run_result.total_testcase_count * self._length))
				total_chars_used += char_count
				result[value] = char_count

		while total_chars_used > self._length:
			maxc = max(result.values())
			for (value, count) in result.items():
				if count == maxc:
					result[value] -= 1
					total_chars_used -= 1

		result_string = [ "[" ]
		for (value, symbol, color) in self._display:
			if value in result:
				result_string.append(f"{color}{symbol * result[value]}{self._clear_color}")
		result_string += [ "]" ]
		return "".join(result_string)


class ResultPrinter():
	class OverviewType(enum.IntEnum):
		BasicOverview = enum.auto()
		RunOverview = enum.auto()

	def __init__(self, db: "Database"):
		self._db = db
		self._output_tz = tzlocal.get_localzone()
		self._color = ResultColorizer()
		self._max_failed_cases_per_action = 2

	def _fmtts(self, utc_ts: datetime.datetime, format_str: str = "full"):
		local_ts = utc_ts.astimezone(self._output_tz)
		match format_str:
			case "full":
				return local_ts.strftime("%Y-%m-%d %H:%M")

			case "time":
				return local_ts.strftime("%H:%M")

			case _:
				raise ValueError(format_str)

	def print_run_overview(self, run_result: "RunResult"):
		result_bar = ResultBar((
			(TestresultStatus.Pass, "+", self._color.green),
			(TestresultStatus.Fail, "-", self._color.red),
			(TestresultStatus.NoAnswer, "_", self._color.red),
			(TestresultStatus.Indeterminate, "?", self._color.yellow),
		), self._color.clr)

		columns = [ ]
		columns.append(f"{run_result.full_id:<9s}")
		columns.append(f"{run_result.multirun.source:<30s}")
		columns.append(f"{run_result.overview['collection']:<25s}")
		ts = f"[ref {run_result.reference_runtime:d} lim {run_result.runtime_allowance:d} act {run_result.runtime:d}]"
		columns.append(f"{ts:<38s}")
		columns.append(f"{result_bar(run_result)}")
		columns.append(f"{run_result.status_text}")
		columns.append(f"{run_result.runtime:d}")
		columns.append(f"{run_result.error_text}")
		print(" ".join(columns))

	def _print_answer(self, testcase_result: dict):
		def print_dict(dict_data: dict, prefix = "\t", color = ""):
			print(color, end = "")
			for line in json.dumps(dict_data, indent = "\t", sort_keys = True).split("\n"):
				print(f"{prefix}{line}")
			print(self._color.clr, end = "")

		status = testcase_result["status"]
		arguments = testcase_result["arguments"]
		correct_reply = testcase_result["correct_reply"]
		received_reply_json = testcase_result["received_reply"]

		print_dict(arguments, color = self._color.cyan)
		print()
		print("    Expected correct reply:")
		print_dict(correct_reply, color = self._color.green)
		print()
		if status != TestresultStatus.NoAnswer:
			print("    Received reply:")
			print_dict(received_reply_json, color = self._color.red)
			print()

	def print_details(self, multirun_result: "MultiRunResult"):
		if multirun_result.build_failed:
			# Build failed.
			print(f"Showing build output of {multirun_result.source} of {multirun_result.solution_author or 'unknown author'}. {self._color.red}Build status {multirun_result.overview['build_status'].name}{self._color.clr} after {multirun_result.build_runtime:r} secs:")
			print(("⎯" * 40) + " stderr " + ("⎯" * 40))
			print(multirun_result.full_overview["build_stderr"].decode("utf-8", errors = "ignore").strip("\r\n"))
			print(("⎯" * 88))
			if multirun_result.overview["build_error_details"] is not None:
				print(multirun_result.overview["build_error_details"]["text"])
		else:
			print(f"Showing testrun summary of {multirun_result.source} of {multirun_result.solution_author or 'unknown author'}. {self._color.green}Build status {multirun_result.overview['build_status'].name}{self._color.clr} after {multirun_result.build_runtime:r} secs:")

			for run_result in multirun_result:
				tr = f"Testrun {multirun_result.multirun_id}.{run_result.run_id}"
				tm = f"{run_result.runtime:r}/{run_result.runtime_allowance:r}"
				print(f"{tr:<17s} {self._color.green if run_result.run_completed else self._color.red}{run_result.collection_name:<25s} {run_result.overview['status'].name:<10s} {tm:<18s}{self._color.clr} {self._color.green if run_result.all_pass else self._color.red}{run_result.status_text}{self._color.clr}")
				if run_result.all_pass:
					continue

				print(f"    {len(run_result.test_failures)} failed testcases recorded, showing the first {self._max_failed_cases_per_action} of each kind:")
				action_count = collections.Counter()
				for failure in run_result.test_failures:
					action_count[failure["status"]] += 1
					if action_count[failure["status"]] > self._max_failed_cases_per_action:
						continue

					print(f"    {'═' * 5} {self._color.red}{failure['status'].name}{self._color.clr} on TC {failure['tc_id']} action {self._color.yellow}{failure['action']}{self._color.clr} {'═' * 5}")
					self._print_answer(failure)
		print()
		print("━" * 88)
		print()

	def _find_all_collections(self, multirun_list: list["MultiRunResult"]):
		collection_list = [ ]
		collection_set = set()
		for multirun_result in multirun_list:
			for run_result in multirun_result:
				collection = run_result.collection_name
				if collection not in collection_set:
					collection_list.append(collection)
					collection_set.add(collection)
		return collection_list

	def print_table(self, multirun_list: list["MultiRunResult"], overview_type: OverviewType = OverviewType.BasicOverview):
		table = Table()
		table.format_columns({
			"source":		CellFormatter(max_length = 18),
			"run_ts":		CellFormatter(content_to_str_fnc = lambda utc_ts: self._fmtts(utc_ts, "full")),
			"name":			CellFormatter(max_length = 30),
			"pass_count":	CellFormatter.basic_ralign(),
			"fail_count":	CellFormatter.basic_ralign(),
			"percentage":	CellFormatter(align = CellFormatter.Alignment.Right, content_to_str_fnc = lambda content: f"{content:.1f}"),
		})
		table.add_row({
			"source":			"Source",
			"run_ts":			"Timestamp",
			"name":				"Author",
			"result_indicator":	"Result",
			"pass_count":		"Pass",
			"fail_count":		"Fail",
			"percentage":		"%",
		}, cell_formatters = {
			"run_ts": table["run_ts"].override(content_to_str_fnc = str),
			"percentage": table["percentage"].override(content_to_str_fnc = str),
		})
		table.add_separator_row()

		collection_list = self._find_all_collections(multirun_list)

		for multirun_result in multirun_list:
			result_indicator = [ ]
			for collection_name in collection_list:
				result = multirun_result[collection_name]
				if result is None:
					result_indicator.append(" ")
				else:
					unique = result.unique_status_result
					if unique is not None:
						result_indicator.append({
							TestresultStatus.Pass:		"✓",
							TestresultStatus.Fail:		"✗",
							TestresultStatus.NoAnswer:	" ",
						}.get(unique, "?"))
					else:
						if result.have_any_of_result(TestresultStatus.Pass):
							# At least one passes:
							result_indicator.append("~")
						else:
							result_indicator.append("✗")
			cell_formatters = { }
			if multirun_result.all_pass:
				cell_formatters["name"] = table["name"].override(color = CellFormatter.Color.Green)
			elif multirun_result.pass_percentage < 50:
				cell_formatters["name"] = table["name"].override(color = CellFormatter.Color.Red)
			elif multirun_result.pass_percentage < 90:
				cell_formatters["name"] = table["name"].override(color = CellFormatter.Color.Yellow)
			table.add_row({
				"source": multirun_result.source,
				"name": multirun_result.solution_author,
				"result_indicator": "".join(result_indicator),
				"pass_count": multirun_result.pass_count,
				"fail_count": multirun_result.nonpass_count,
				"percentage": multirun_result.pass_percentage,
				"run_ts": multirun_result.build_start_utcts,
			}, cell_formatters = cell_formatters)

			if overview_type == self.OverviewType.RunOverview:
				# Print results for each run
				for run_result in multirun_result:
					cell_formatters = { }
					if run_result.all_pass:
						cell_formatters["name"] = table["name"].override(color = CellFormatter.Color.Green)
					elif run_result.pass_percentage < 50:
						cell_formatters["name"] = table["name"].override(color = CellFormatter.Color.Red)
					elif run_result.pass_percentage < 90:
						cell_formatters["name"] = table["name"].override(color = CellFormatter.Color.Yellow)

					if run_result.overview["status"] != TestrunStatus.Finished:
						cell_formatters["result_indicator"] = CellFormatter(color = CellFormatter.Color.Red)

					table.add_row({
						"name": run_result.collection_name,
						"result_indicator": run_result.overview["status"].name,
						"pass_count": run_result.pass_count,
						"fail_count": run_result.nonpass_count,
						"percentage": run_result.pass_percentage,
					}, cell_formatters = cell_formatters)

		match overview_type:
			case self.OverviewType.BasicOverview:
				table.print("source", "run_ts", "name", "result_indicator", "pass_count", "fail_count", "percentage")

			case self.OverviewType.RunOverview:
				table.print("source", "name", "result_indicator", "pass_count", "fail_count", "percentage")

			case _:
				raise NotImplementedError(overview_type)
