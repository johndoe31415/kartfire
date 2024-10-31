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

class ResultPrinter():
	def __init__(self, results: dict):
		self._results = results
		self._results_by_repo = { }
		for solution in self._results["content"]:
			self._results_by_repo[solution["dut"]["dirname"]] = solution

	def print_result(self, repo_name: str):
		solution = self._results_by_repo[repo_name]
		basename = os.path.basename(repo_name)
		print(f"{basename:>20s}: {solution['statistics']['*']['passed']} / {solution['statistics']['*']['total']} {100 * solution['statistics']['*']['passed'] / solution['statistics']['*']['total']:.1f}%")

	def print(self):
		for repo_name in sorted(self._results_by_repo):
			self.print_result(repo_name)

	@classmethod
	def from_file(cls, json_filename: str):
		with open(json_filename) as f:
			return cls(results = json.load(f))
