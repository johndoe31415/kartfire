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

import json
from .BaseAction import BaseAction

class ActionMerge(BaseAction):
	def _load_results(self, filename: str):
		with open(filename) as f:
			testrun_results = json.load(f)
		if testrun_results["meta"]["type"] != "testcase_results":
			raise ValueError(f"Not a testcase result file: {filename}")
		return testrun_results


	def run(self):
		src = self._load_results(self._args.source_filename)
		try:
			dst = self._load_results(self._args.destination_filename)
		except FileNotFoundError:
			dst = src

		src_content_by_dut = { report["dut"]["dirname"]: report for report in src["content"] }
		dst_content_by_dut = { report["dut"]["dirname"]: report for report in dst["content"] }

		dst_content_by_dut.update(src_content_by_dut)
		dst["content"] = list(dst_content_by_dut.values())

		with open(self._args.destination_filename, "w") as f:
			json.dump(dst, f)
