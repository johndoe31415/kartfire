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

class RunResult():
	def __init__(self, db: "Database", run_id: int):
		self._db = db
		self._run_id = run_id

	@property
	def run_id(self):
		return self._run_id

	@property
	def runtime(self):
		return TimeDelta(self.overview["run_start_utcts"], self.overview["run_end_utcts"])

	@functools.cached_property
	def overview(self):
		return self._db.get_run_overview(self._run_id)

	@functools.cached_property
	def full_overview(self):
		return self._db.get_run_overview(self._run_id, full_overview = True)

	@functools.cached_property
	def result_count(self):
		return self._db.get_run_result_count(self._run_id)

	@functools.cached_property
	def result_count_dict(self):
		return { status: count for (status, count) in self.result_count }

	@functools.cached_property
	def testresult_details(self):
		return self._db.get_run_details(self._run_id)

	@functools.cached_property
	def total_testcase_count(self):
		return sum(count for (status, count) in self.result_count)

	@property
	def have_results(self):
		return len(self.result_count) > 0

	@property
	def have_git_info(self):
		source_metadata = self.overview["source_metadata"]
		return ("meta" in source_metadata) and ("git" in source_metadata["meta"]) and ("commit" in source_metadata["meta"]["git"])

	@property
	def status_text(self):
		if len(self.result_count) == 1:
			return f"All {self.result_count[0][0].name}"
		else:
			return ", ".join(f"{count}/{count / self.total_testcase_count * 100:.1f}% {status.name}" for (status, count) in self.result_count)

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
			return "unknown author"

	@property
	def error_text(self):
		if self.overview["error_details"] is not None:
			return self.overview["error_details"]["text"]
		else:
			return ""
