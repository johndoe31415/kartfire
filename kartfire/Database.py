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

import sqlite3
import json
import contextlib
import datetime
import enum
from .Testcase import Testcase, TestcaseCollection

class TestrunStatus(enum.Enum):
	Running = "running"				# Still running
	Finished = "finished"			# Run ran to completion
	Failed = "failed"				# Something failed to start the run (e.g., docker container start error)
	BuildFailed = "build_failed"	# Build step failed
	Aborted = "aborted"				# User aborted run (e.g., Ctrl-C)
	Terminated = "terminated"		# Run aborted (e.g., timeout or killed because of excessive resource use)

class TestresultStatus(enum.Enum):
	NoAnswer = "no_answer"
	Pass = "pass"
	Fail = "fail"

class Database():
	def __init__(self, filename: str):
		self._change_count = 0
		self._conn = sqlite3.connect(filename)
		self._conn.row_factory = sqlite3.Row
		self._cursor = self._conn.cursor()

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""\
			CREATE TABLE testcases (
				tcid integer PRIMARY KEY,
				action char(64) NOT NULL,
				query varchar(4096) NOT NULL,
				correct_response varchar(4096) NULL,
				dependencies varchar(1024) NULL,
				reference_runtime_secs float NULL,
				created_ts varchar(64) NOT NULL,
				UNIQUE(action, query)
			);
			""")

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""\
			CREATE TABLE testrun (
				runid integer PRIMARY KEY,
				source varchar(256),
				source_metadata varchar(4096),
				run_start_ts varchar(64) NOT NULL,
				run_end_ts varchar(64) NULL,
				max_permissible_runtime_secs float NOT NULL,
				max_permissible_ram_mib integer NOT NULL,
				dependencies varchar(4096) NOT NULL,
				status varchar(256),
				CHECK((status = 'running') OR (status = 'finished') OR (status = 'failed') OR (status = 'build_failed') OR (status = 'aborted') OR (status = 'terminated'))
			);
			""")

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""\
			CREATE TABLE testresult (
				tcid integer REFERENCES testcases(tcid),
				runid integer REFERENCES testrun(runid),
				received_result varchar(4096) NULL,
				status varchar(16) NOT NULL DEFAULT 'no_answer',
				UNIQUE(tcid, runid),
				CHECK((status = 'no_answer') OR (status = 'pass') OR (status = 'fail'))
			);
			""")

	@staticmethod
	def _dict2str(values: dict):
		return json.dumps(values, sort_keys = True, separators = (",", ":"))

	def _insert(self, table_name: str, value_dict: dict):
		fields = list(value_dict)
		values = [ value_dict[field] for field in fields ]
		query = f"INSERT INTO {table_name} ({','.join(field for field in fields)}) VALUES ({','.join([ '?' ] * len(fields))});"
		self._cursor.execute(query, values)
		self._change_count += 1

	def create_testcase(self, action: str, query: dict, created_ts: datetime.datetime, correct_response: dict | None = None, dependencies: dict | None = None, reference_runtime_secs: float | None = None):
		self._insert("testcases", {
			"action": action,
			"query": self._dict2str(query),
			"created_ts": created_ts.isoformat(),
			"correct_response": None if (correct_response is None) else self._dict2str(correct_response),
			"dependencies": None if (dependencies is None) else self._dict2str(dependencies),
			"reference_runtime_secs": reference_runtime_secs,
		})

	def _get_tcids_for_selector_part(self, testcase_selector_part: str):
		if testcase_selector_part.isdigit():
			return set([ int(testcase_selector_part) ])
		elif testcase_selector_part == "*":
			return set(row["tcid"] for row in self._cursor.execute("SELECT tcid FROM testcases;").fetchall())
		elif testcase_selector_part.startswith("@"):
			action = testcase_selector_part[1:]
			return set(row["tcid"] for row in self._cursor.execute("SELECT tcid FROM testcases WHERE action = ?;", (action, )).fetchall())
		else:
			raise ValueError(f"Invalid testcase selector: {testcase_selector_part}")

	def _get_testcase(self, tcid: int) -> Testcase:
		row = dict(self._cursor.execute("SELECT action, query, correct_response, dependencies, reference_runtime_secs FROM testcases WHERE tcid = ?;", (tcid, )).fetchone())
		for key in [ "query", "correct_response", "dependencies" ]:
			if row[key] is not None:
				row[key] = json.loads(row[key])
		row["tcid"] = tcid
		return Testcase(**row)

	def _get_testcase_collection_from_tcids(self, tcids: set[int]) -> TestcaseCollection:
		testcases = [ self._get_testcase(tcid) for tcid in tcids ]
		return TestcaseCollection(testcases)

	def get_testcase_collection(self, testcase_selector: str):
		tcids = set()
		for testcase_selector_part in [ part.strip() for part in testcase_selector.split(",") ]:
			tcids |= self._get_tcids_for_selector_part(testcase_selector_part)
		return self._get_testcase_collection_from_tcids(tcids)

	def opportunistic_commit(self, max_change_count: int = 100):
		if self._change_count > max_change_count:
			self.commit()

	def commit(self):
		self._conn.commit()
		self._change_count = 0
