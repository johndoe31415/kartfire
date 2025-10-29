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

import functools
from .TimeDelta import TimeDelta
from .Enums import TestrunStatus

class RunResult():
	def __init__(self, db: "Database", multirun: "MultiRunResult", overview: dict):
		self._db = db
		self._multirun = multirun
		self._overview = overview

	@property
	def full_id(self):
		return f"{self.multirun.multirun_id}.{self.run_id}"

	@property
	def run_id(self):
		return self._overview["run_id"]

	@property
	def multirun(self):
		return self._multirun

	@property
	def overview(self):
		return self._overview

	@property
	def runtime(self):
		return TimeDelta(self.overview["runtime_secs"])

	@property
	def runtime_allowance(self):
		return TimeDelta(self.overview["runtime_allowance_secs"])

	@property
	def reference_runtime(self):
		return TimeDelta(self.overview["reference_runtime_secs"])

	@property
	def collection_name(self):
		return self.overview["collection"]

	@functools.cached_property
	def full_overview(self):
		return self._db.get_run_overview(self.run_id, full_overview = True)

	@functools.cached_property
	def result_count(self):
		return self._db.get_run_result_count(self.run_id)

	@functools.cached_property
	def result_count_dict(self):
		return { status: count for (status, count) in self.result_count }

	@functools.cached_property
	def testresult_details(self):
		return self._db.get_run_details(self.run_id)

	@functools.cached_property
	def total_testcase_count(self):
		return sum(count for (status, count) in self.result_count)

	@property
	def have_results(self):
		return len(self.result_count) > 0

	@property
	def status_text(self):
		if len(self.result_count) == 1:
			return f"All {self.result_count[0][0].name}"
		else:
			return ", ".join(f"{count}/{count / self.total_testcase_count * 100:.1f}% {status.name}" for (status, count) in self.result_count)

	@property
	def error_text(self):
		if self.overview["error_details"] is not None:
			return self.overview["error_details"]["text"]
		else:
			return ""

class MultiRunResult():
	def __init__(self, db: "Database", multirun_id: int, preloaded_runs: list[RunResult] | None = None):
		self._db = db
		self._multirun_id = multirun_id
		self._overview = db.get_multirun_overview(multirun_id)
		if preloaded_runs is not None:
			self._run_results = preloaded_runs
		else:
			self._run_results = [ RunResult(db, self, run_result) for run_result in self._db.get_run_overviews_of_multirun(self._multirun_id) ]

	@property
	def multirun_id(self):
		return self._multirun_id

	@property
	def overview(self):
		return self._overview

	@property
	def shortname(self):
		return self.overview["source"]

	@property
	def build_failed(self):
		return self.overview["build_status"] != TestrunStatus.Finished

	@classmethod
	def load_single_run(cls, db: "Database", run_id: int):
		run_overview = db.get_run_overview(run_id)
		multirun_overview = db.get_multirun_overview(run_overview["multirun_id"])
		run_result = RunResult(db, None, run_overview)
		multirun = cls(db = db, multirun_id = multirun_overview["multirun_id"], preloaded_runs = [ run_result ])
		run_result._multirun = multirun
		return run_result


	@property
	def have_git_info(self):
		source_metadata = self.overview["source_metadata"]
		return ("meta" in source_metadata) and ("git" in source_metadata["meta"]) and ("commit" in source_metadata["meta"]["git"])

	@property
	def source(self):
		if self.have_git_info:
			return f"{self.overview['source']}:{self.overview['source_metadata']['meta']['git']['shortcommit']}"
		else:
			return f"{self.overview['source']}"

	@property
	def solution_author(self):
		try:
			return self.overview["source_metadata"]["meta"]["json"]["kartfire"]["name"]
		except KeyError:
			return None

	@property
	def solution_email(self):
		try:
			return self.overview["source_metadata"]["meta"]["json"]["kartfire"]["email"]
		except KeyError:
			return None

	@property
	def build_error_text(self):
		if self.overview["build_error_details"] is not None:
			return self.overview["build_error_details"]["text"]
		else:
			return ""

	@property
	def build_allowance(self):
		return TimeDelta(self.overview["build_runtime_allowance_secs"])

	@property
	def build_runtime(self):
		return TimeDelta(self.overview["build_runtime_secs"])

	@property
	def test_runtime(self):
		return TimeDelta(sum(run_result.overview["runtime_secs"] for run_result in self))

	@property
	def test_reference_runtime(self):
		return TimeDelta(sum(run_result.overview["reference_runtime_secs"] for run_result in self))

	def __len__(self):
		return len(self._run_results)

	def __iter__(self):
		return iter(self._run_results)


