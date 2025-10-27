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

@dataclasses.dataclass(slots = True, order = True, frozen = True)
class Testcase():
	tc_id: int
	action: str
	arguments: dict
	correct_reply: dict | None = None
	dependencies: dict | None = None
	contained_collections: set | None = None		# Not necessarily populated

	def guest_dict(self):
		return {
			"action": self.action,
			"arguments": self.arguments,
		}

	def __format__(self, fmtstr: str):
		if self.contained_collections is None:
			contained = ""
		else:
			contained = f"[ {', '.join(sorted(self.contained_collections))} ]"
		return f"{self.tc_id:5d} {self.action:<15s} {contained:<15s} {str(self.arguments)[:70]:70}  =>  {'?' if self.correct_reply is None else str(self.correct_reply)[:30]}"

class TestcaseCollection():
	def __init__(self, name: str, testcases: list[Testcase], reference_runtime_secs: float | None = None):
		self._name = name
		self._testcases = testcases
		self._reference_runtime_secs = reference_runtime_secs
		self._testcases.sort(key = lambda tc: (tc.action, tc.tc_id))
		self._testcases_by_tc_id = { tc.tc_id: tc for tc in self._testcases }
		self._dependencies = self._compute_dependencies()

	@property
	def name(self):
		return self._name

	@property
	def dependencies(self):
		return self._dependencies

	@property
	def reference_runtime_secs(self):
		return self._reference_runtime_secs

	def _compute_dependencies(self):
		dependencies = { }
		dependency_src = { }
		for tc in self._testcases:
			if tc.dependencies is not None:
				for (dependency_key, dependency_parameters) in tc.dependencies.items():
					if (dependency_key not in dependencies):
						dependencies[dependency_key] = dependency_parameters
						dependency_src[dependency_key] = tc
					elif dependencies[dependency_key] != dependency_parameters:
						raise ValueError(f"Incompatible testcase dependencies. TC {tc.tc_id} and {dependency_src[dependency_key].tc_id} both require a dependency called {dependency_key}, but with incompatible arguments. {tc.tc_id}={dependency_parameters} while {dependency_src[dependency_key].tc_id}={dependency_src[dependency_key].dependencies[dependency_key]}")
		return dependencies

	def print(self):
		for testcase in self._testcases:
			print(f"{testcase}")

	def __contains__(self, tc_id: int):
		return tc_id in self._testcases_by_tc_id

	def __len__(self):
		return len(self._testcases)

	def __iter__(self):
		return iter(self._testcases)

	def __getitem__(self, tc_id: int):
		return self._testcases_by_tc_id[tc_id]

	def __str__(self):
		return f"Collection \"{self.name}\": {len(self._testcases)} TCs, nominal runtime {'unknown' if (self.reference_runtime_secs is None) else f'{self.reference_runtime_secs:.0f} secs'}"
