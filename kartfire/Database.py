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
from .Testcase import Testcase, TestcaseCollection
from .Enums import TestrunStatus, TestresultStatus
from .Exceptions import NoSuchCollectionException

class Database():
	def __init__(self, filename: str):
		self._change_count = 0
		self._conn = sqlite3.connect(filename)
		self._conn.row_factory = sqlite3.Row
		self._cursor = self._conn.cursor()

		# Five minutes of blocking time before giving up
		self._cursor.execute(f"PRAGMA busy_timeout = {5 * 60 * 1000}")

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""\
			CREATE TABLE testcases (
				tcid integer PRIMARY KEY,
				action char(64) NOT NULL,
				query varchar(4096) NOT NULL,
				correct_response varchar(4096) NULL,
				dependencies varchar(1024) NULL,
				created_ts varchar(64) NOT NULL,
				UNIQUE(action, query)
			);
			""")

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""\
			CREATE TABLE testrun (
				runid integer PRIMARY KEY,
				collectionid integer NOT NULL,
				source varchar(256),
				source_metadata varchar(4096),
				run_start_ts varchar(64) NOT NULL,
				run_end_ts varchar(64) NULL,
				max_permissible_runtime_secs float NOT NULL,
				max_permissible_ram_mib integer NOT NULL,
				dependencies varchar(4096) NOT NULL,
				status varchar(256) NOT NULL DEFAULT 'running',
				error_details varchar(1024) NULL,
				stderr blob NULL,
				CHECK((status = 'running') OR (status = 'finished') OR (status = 'failed') OR (status = 'build_failed') OR (status = 'aborted') OR (status = 'terminated'))
			);
			""")

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""\
			CREATE TABLE testcollection (
				name varchar(128) PRIMARY KEY,
				collectionid integer NOT NULL UNIQUE,
				reference_runtime_secs float NULL
			);
			""")

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""\
			CREATE TABLE testcollection_testcases (
				collectionid integer NOT NULL REFERENCES testcollection(collectionid),
				tcid integer NOT NULL REFERENCES testcases(tcid),
				UNIQUE(collectionid, tcid)
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
				CHECK((status = 'no_answer') OR (status = 'pass') OR (status = 'fail') OR (status = 'indeterminate'))
			);
			""")

	@staticmethod
	def _dict2str(values: dict):
		return json.dumps(values, sort_keys = True, separators = (",", ":"))

	@staticmethod
	def utcnow():
		return datetime.datetime.now(datetime.UTC).isoformat()[:-6] + "Z"

	def _insert(self, table_name: str, value_dict: dict):
		fields = list(value_dict)
		values = [ value_dict[field] for field in fields ]
		query = f"INSERT INTO {table_name} ({','.join(field for field in fields)}) VALUES ({','.join([ '?' ] * len(fields))});"
		result = self._cursor.execute(query, values)
		self._change_count += 1
		return result.lastrowid

	def create_testcase(self, action: str, query: dict, created_ts: datetime.datetime, correct_response: dict | None = None, dependencies: dict | None = None):
		self._insert("testcases", {
			"action": action,
			"query": self._dict2str(query),
			"created_ts": created_ts.isoformat(),
			"correct_response": None if (correct_response is None) else self._dict2str(correct_response),
			"dependencies": None if (dependencies is None) else self._dict2str(dependencies),
		})

	def create_testrun(self, submission: "Submission", testcases: "TestcaseCollection"):
		runid = self._insert("testrun", {
			"source": submission.shortname,
			"source_metadata": self._dict2str(submission.to_dict()),
			"run_start_ts": self.utcnow(),
			"max_permissible_runtime_secs": 999999,
			"max_permissible_ram_mib": 999999,
			"dependencies": "TODO",
			"status": "running",
		})
		for testcase in testcases:
			self._insert("testresult", {
				"tcid":		testcase.tcid,
				"runid":	runid,
			})
		return runid

	def update_testresult(self, runid: int, tcid: int, received_result: dict, test_result_status: TestresultStatus):
		self._cursor.execute("UPDATE testresult SET received_result = ?, status = ? WHERE (tcid = ?) AND (runid = ?);", (self._dict2str(received_result), test_result_status.value, tcid, runid))
		self._change_count += 1

	def close_testrun(self, runid: int, submission_run_result: "SubmissionRunResult"):
		self._cursor.execute("UPDATE testrun SET status = ?, error_details = ?, run_end_ts = ?, stderr = ? WHERE runid = ?;", (submission_run_result.testrun_status.value, submission_run_result.error_details, self.utcnow(), submission_run_result.stderr, runid))
		self._change_count += 1

	def _get_tcids_for_selector_part(self, testcase_selector_part: str):
		if testcase_selector_part.isdigit():
			return set([ int(testcase_selector_part) ])
		elif testcase_selector_part == "*":
			return set(row["tcid"] for row in self._cursor.execute("SELECT tcid FROM testcases;").fetchall())
		elif testcase_selector_part.startswith("@"):
			action = testcase_selector_part[1:]
			return set(row["tcid"] for row in self._cursor.execute("SELECT tcid FROM testcases WHERE action = ?;", (action, )).fetchall())
		else:
			raise NoSuchCollectionException(f"Invalid testcase selector: {testcase_selector_part}")

	def get_tcids_by_selector(self, testcase_selector: str) -> set[int]:
		tcids = set()
		for testcase_selector_part in [ part.strip() for part in testcase_selector.split(",") ]:
			tcids |= self._get_tcids_for_selector_part(testcase_selector_part)
		return tcids

	def _get_testcase(self, tcid: int) -> Testcase:
		row = dict(self._cursor.execute("SELECT action, query, correct_response, dependencies FROM testcases WHERE tcid = ?;", (tcid, )).fetchone())
		for key in [ "query", "correct_response", "dependencies" ]:
			if row[key] is not None:
				row[key] = json.loads(row[key])
		row["tcid"] = tcid
		return Testcase(**row)

	def _get_collectionid(self, collection_name: str) -> int:
		collectionid = self._cursor.execute("SELECT collectionid FROM testcollection WHERE name = ? LIMIT 1 COLLATE NOCASE;", (collection_name, )).fetchone()
		if collectionid is None:
			raise NoSuchCollectionException(f"No such test case collection: {collection_name}")
		return collectionid["collectionid"]

	def add_tcids_to_collection(self, collection_name: str, tcids: set[int]) -> None:
		collectionid = self._get_collectionid(collection_name)
		for tcid in tcids:
			self._insert("testcollection_testcases", {
				"collectionid": 1,
				"tcid": tcid,
			})

	def remove_tcids_from_collection(self, collection_name: str, tcids: set[int]) -> None:
		collectionid = self._get_collectionid(collection_name)
		for tcid in tcids:
			self._cursor.execute("DELETE FROM testcollection_testcases WHERE (collectionid = ?) AND (tcid = ?);", (collectionid, tcid))

	def get_testcase_collection(self, collection_name: str) -> TestcaseCollection:
		collectionid = self._get_collectionid(collection_name)
		row = self._cursor.execute("SELECT name, reference_runtime_secs FROM testcollection WHERE collectionid = ?;", (collectionid, )).fetchone()
		tcids = set(row["tcid"] for row in self._cursor.execute("SELECT tcid FROM testcollection_testcases WHERE collectionid = ?;", (collectionid, )).fetchall())
		testcases = [ self._get_testcase(tcid) for tcid in tcids ]
		return TestcaseCollection(name = row["name"], testcases = testcases, reference_runtime_secs = row["reference_runtime_secs"])

	def create_collection(self, collection_name: str):
		self._change_count += 1
		return self._cursor.execute("INSERT INTO testcollection (collectionid, name) VALUES ((SELECT COALESCE(MAX(collectionid) + 1, 1) FROM testcollection), ?);", (collection_name, )).lastrowid

	def opportunistic_commit(self, max_change_count: int = 100):
		if self._change_count > max_change_count:
			self.commit()

	def commit(self):
		self._conn.commit()
		self._change_count = 0
