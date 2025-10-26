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

import datetime
import tzlocal
import pytz
import json
import collections
from .Enums import TestrunStatus, TestresultStatus
from .RunResult import RunResult

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

class ResultBar():
	def __init__(self, display: tuple, clear_color: str, length: int = 30):
		self._display = display
		self._clear_color = clear_color
		self._length = length

	def __call__(self, run_result: RunResult):
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
	def __init__(self, db: "Database"):
		self._db = db
		self._output_tz = tzlocal.get_localzone()
		self._color = ResultColorizer()

	def _fmtts(self, utc_ts: datetime.datetime, format_str: str = "full"):
		local_ts = utc_ts.astimezone(self._output_tz)
		match format_str:
			case "full":
				return local_ts.strftime("%Y-%m-%d %H:%M")

			case "time":
				return local_ts.strftime("%H:%M")

			case _:
				raise ValueError(format_str)

	def print_overview(self, run_id: int):
		run_result = RunResult(self._db, run_id)

#		td = TimeDelta(row["run_start_utcts"], row["run_end_utcts"])
#		error_details = row["error_details"]

		result_bar = ResultBar((
			(TestresultStatus.Pass, "+", self._color.green),
			(TestresultStatus.Fail, "-", self._color.red),
			(TestresultStatus.NoAnswer, "_", self._color.red),
			(TestresultStatus.Indeterminate, "?", self._color.yellow),
		), self._color.clr)

		columns = [ ]

		columns.append(f"{run_result.run_id:5d}")
		columns.append(f"{run_result.source:<30s}")
		columns.append(f"{result_bar(run_result)}")
		columns.append(f"{run_result.status_text}")


#		columns = [
#			f"{row['run_id']:5d}",
#			f"{source_str:25s}",
#			f"{TestrunStatus(row['status']).name:14s}",
#			f"  {self._fmtts(row['run_start_utcts'])}-{self._fmtts(row['run_end_utcts'], 'time')} ({td})",
#			f"  runtime {td:d}  ",
#			f"  {result_bar(row['result_count'])}"
#			f"  {sorted_status_str}"
#		]
#
#		if error_details is not None:
#			columns.append(f"{error_details['text']}")
		print(" ".join(columns))

	def _print_answer(self, run_details: dict, testcase_result: dict):
		testcase = testcase_result["testcase"]
		status = TestresultStatus(testcase_result["status"])
		arguments = testcase.arguments
		correct_reply = testcase.correct_reply
		received_reply_json = json.loads(testcase_result["received_reply_json"])
		print(f"Testcase {testcase.tc_id} of run {run_details['run_id']} marked as {status.name}. Action \"{testcase.action}\", arguments:")
		print(json.dumps(arguments, indent = "\t", sort_keys = True))
		print()
		print("Correct reply:")
		print(json.dumps(correct_reply, indent = "\t", sort_keys = True))
		print()
		print("Received reply:")
		print(json.dumps(received_reply_json, indent = "\t", sort_keys = True))
		print()
		print("~" * 120)

	def print_details(self, run_id: int):
		max_failed_cases_per_action = 2
		row = self._db.get_run_details(run_id)
		source_meta = json.loads(row["source_metadata"])
		if ("meta" in source_meta) and ("git" in source_meta["meta"]) and ("shortcommit" in source_meta["meta"]["git"]):
			source_str = f"{row['source']}:{source_meta['meta']['git']['shortcommit']}"
		else:
			source_str = f"{row['source']}"

		try:
			user_name = source_meta["meta"]["json"]["kartfire"]["name"]
		except KeyError:
			user_name = "unknown author"
		print(f"Showing failed cases of {source_str} of {user_name} run ID {run_id}, max of {max_failed_cases_per_action} fails per action")

		action_count = collections.Counter()
		for result in row["results"]:
			status = TestresultStatus(result["status"])
			if status == TestresultStatus.Fail:
				action_count[result["testcase"].action] += 1
				if action_count[result["testcase"].action] <= max_failed_cases_per_action:
					self._print_answer(row, result)
