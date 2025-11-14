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
import collections
from .Enums import TestresultStatus

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

class TestcaseCollectionEvaluation():
	def __init__(self, tc_collection: "TestcaseCollection", record_max_failed_reply_count = 5):
		self._tc_collection = tc_collection
		self._record_max_failed_reply_count = record_max_failed_reply_count
		self._status_by_tc_id = { }
		self._recorded_replies = collections.defaultdict(dict)
		self._allow_further_replies = True

	def received_trusted_msg(self, msg: dict):
		if msg["type"] == "time":
			# This indicates that the main test process has finished. In
			# theory, the DUT could trick us by double forking (so we would
			# record the end of the process) and then, as a background task,
			# still produce output. To prevent this, we disallow any further
			# replies after timing had stopped.
			self._allow_further_replies = False

	def received_reply(self, json_data: dict):
		if not self._allow_further_replies:
			return
		if "id" not in json_data:
			return
		if "reply" not in json_data:
			return
		if not json_data["id"].isdigit():
			return

		tc_id = int(json_data["id"])
		if tc_id not in self._tc_collection:
			# Testcase has an reply that was never asked
			return

		if tc_id in self._status_by_tc_id:
			# Given the same reply twice, ignore.
			return

		# Determine status
		testcase = self._tc_collection[tc_id]
		if testcase.correct_reply is None:
			# No response available
			test_result_status = TestresultStatus.Indeterminate
		elif testcase.correct_reply == json_data["reply"]:
			test_result_status = TestresultStatus.Pass
		else:
			test_result_status = TestresultStatus.Fail
		self._status_by_tc_id[tc_id] = test_result_status

		# Do we need to save the reply?
		if ((test_result_status == TestresultStatus.Indeterminate) or
			((test_result_status == TestresultStatus.Fail) and (len(self._recorded_replies[TestresultStatus.Fail]) < self._record_max_failed_reply_count))):
			# Either it's indeterminate (then we always save the reply so that
			# we can build a reference) or it's Fail (then we only collect the
			# first 5 or so)
			self._recorded_replies[test_result_status][tc_id] = json_data["reply"]

	@property
	def test_failures(self):
		for (test_result_status, cases) in self._recorded_replies.items():
			for (tc_id, reply) in cases.items():
				yield (tc_id, test_result_status, reply)

		# Determine TCIDs of NoAnswer replies so we can save those as well
		noanswer_tc_ids = set(self._tc_collection.tc_ids) - set(self._status_by_tc_id.keys())
		for (no, tc_id) in enumerate(noanswer_tc_ids):
			if no >= self._record_max_failed_reply_count:
				break
			yield (tc_id, TestresultStatus.NoAnswer, None)

	@property
	def test_summary(self):
		counter = collections.Counter(self._status_by_tc_id.values())
		missing_replies = len(self._tc_collection) - counter.total()
		if missing_replies > 0:
			counter[TestresultStatus.NoAnswer] = missing_replies
		return counter


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
	def tc_ids(self):
		return self._testcases_by_tc_id.keys()

	@property
	def reference_runtime_secs(self):
		return self._reference_runtime_secs

	def prepare_evaluation(self):
		return TestcaseCollectionEvaluation(self)

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

	def to_dict(self):
		return {
			"name": self.name,
			"length": len(self),
			"reference_runtime_secs": self.reference_runtime_secs,
		}
