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
from .BaseAction import BaseAction

class FiletypeComposition():
	def __init__(self, filetype_dict: dict):
		self._count = self._determine_programming_languages(filetype_dict)
		self._total_lines = sum(lines for (lines, language) in self._count)

	@property
	def loc(self):
		return self._total_lines

	def _determine_programming_languages(self, filetype_dict: dict) -> dict:
		count = collections.defaultdict(int)
		for (ext, lines) in filetype_dict.items():
			language = {
				".c":		"C",
				".h":		"C",
				".py":		"Python",
				".rs":		"Rust",
				".java":	"Java",
				".jl":		"Julia",
				".go":		"Go",
				".s":		"Assembly",
				".cpp":		"C++",
				".hpp":		"C++",
				".cc":		"C++",
				".hh":		"C++",
			}.get(ext.lower())
			if language is not None:
				count[language] += lines
		count = [ (lines, language) for (language, lines) in count.items() ]
		count.sort(reverse = True)
		return count

	def __format__(self, fmtstr: str):
		if len(self._count) == 0:
			return "unknown"
		else:
			return ", ".join(f"{lines / self._total_lines * 100:.0f}% {language}" for (lines, language) in self._count)

	def __str__(self):
		return format(self)

class ActionLeaderboard(BaseAction):
	ResultEntry = collections.namedtuple("ResultEntry", [ "correct_ratio", "solution_name", "time_secs", "filetypes" ])

	def _record_solution(self, solution: dict):
		total_runtime_secs = 0
		for testbatch in solution["testbatches"].values():
			total_runtime_secs += testbatch["runtime_secs"]

		ratio = solution["statistics_by_action"]["*"]["passed"] / solution["statistics_by_action"]["*"]["total"]
		filetypes = FiletypeComposition(solution["dut"]["meta"].get("filetypes", { }))
		entry = self.ResultEntry(correct_ratio = ratio, solution_name = os.path.basename(solution["dut"]["dirname"]), time_secs = total_runtime_secs, filetypes = filetypes)
		self._results.append(entry)

	def run(self):
		self._results = [ ]
		with open(self._args.testrun_filename) as f:
			test_results = json.load(f)

		for solution in test_results["content"]:
			self._record_solution(solution)
		self._results.sort(key = lambda entry: (-entry.correct_ratio, entry.time_secs, entry.solution_name))
		sep_line = False
		for (pos, entry) in enumerate(self._results, 1):
			time_millis = round(entry.time_secs * 1000)
			time_secs = int(entry.time_secs)
			if (not sep_line) and entry.correct_ratio != 1:
				print("⎯" * 60)
				sep_line = True
			print(f"{pos:3d}  {entry.solution_name:25s} {time_secs // 60:4d}:{time_secs % 60:02d}   {entry.correct_ratio * 100:5.1f}%    {str(entry.filetypes):<30s}   {entry.filetypes.loc} LOCs")
		return 0
