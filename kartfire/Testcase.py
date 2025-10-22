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

import dataclasses

@dataclasses.dataclass
class Testcase():
	tcid: int
	action: str
	query: dict
	correct_response: dict | None = None
	dependencies: dict | None = None
	reference_runtime_secs: float | None = None

	def guest_dict(self):
		return {
			"action": self.action,
			"arguments": self.query,
		}

	def __format__(self, fmtstr: str):
		return f"{self.tcid:5d} {self.action:<15s} {self.query}"

class TestcaseCollection():
	def __init__(self, testcases: list[Testcase]):
		self._testcases = testcases
		self._testcases.sort(key = lambda tc: (tc.action, tc.tcid))
		self._testcases_by_tcid = { tc.tcid: tc for tc in self._testcases }

	def print(self):
		for testcase in self._testcases:
			print(f"{testcase}")

	def __contains__(self, tcid: int):
		return tcid in self._testcases_by_tcid

	def __len__(self):
		return len(self._testcases)

	def __iter__(self):
		return iter(self._testcases)

	def __getitem__(self, tcid: int):
		return self._testcases_by_tcid[tcid]

	def __str__(self):
		return f"{len(self._testcases)} TCs"
