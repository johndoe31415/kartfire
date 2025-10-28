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
import collections
import os
from .SqliteORM import SqliteORM
from .Testcase import Testcase, TestcaseCollection
from .Enums import TestrunStatus, TestresultStatus
from .Exceptions import NoSuchCollectionException, NoDatabaseFoundException

class Database(SqliteORM):
	def __init__(self, filename: str):
		if not os.path.isfile(filename):
			raise NoDatabaseFoundException(f"There is no kartfire database at {filename}. Create an empty file if you want one to be created.")

		super().__init__(filename)
		self._map_type("testcases:arguments", "json")
		self._map_type("testcases:correct_reply", "json")
		self._map_type("testcases:dependencies", "json")
		self._map_type("testcases:created_utcts", "utcts")

		self._map_type("testrun:source_metadata", "json")
		self._map_type("testrun:run_start_utcts", "utcts")
		self._map_type("testrun:run_end_utcts", "utcts")
		self._map_type("testrun:dependencies", "json")
		self._map_type("testrun:status", "enum", TestrunStatus)
		self._map_type("testrun:error_details", "json")

		self._map_type("testresult:received_reply", "json")
		self._map_type("testresult:status", "enum", TestresultStatus)

		# Five minutes of blocking time before giving up
		self._cursor.execute(f"PRAGMA busy_timeout = {5 * 60 * 1000}")

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""\
			CREATE TABLE testcases (
				tc_id integer PRIMARY KEY,
				action varchar(64) NOT NULL,
				arguments varchar(4096) NOT NULL,
				correct_reply varchar(4096) NULL,
				dependencies varchar(1024) NULL,
				created_utcts varchar(64) NOT NULL,
				UNIQUE(action, arguments)
			);
			""")

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""\
			CREATE TABLE testcollection (
				name varchar(128) PRIMARY KEY,
				collection_id integer NOT NULL UNIQUE,
				reference_runtime_secs float NULL
			);
			""")

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""\
			CREATE TABLE testrun (
				run_id integer PRIMARY KEY,
				collection varchar(128) NOT NULL REFERENCES testcollection(name),
				source varchar(256),
				source_metadata varchar(4096),
				run_start_utcts varchar(64) NOT NULL,
				run_end_utcts varchar(64) NULL,
				max_permissible_runtime_secs float NOT NULL,
				max_permissible_ram_mib integer NOT NULL,
				dependencies varchar(4096) NOT NULL,
				status varchar(32) NOT NULL DEFAULT 'running',
				error_details varchar(4096) NULL,
				stderr blob NULL,
				CHECK((status = 'running') OR (status = 'finished') OR (status = 'failed') OR (status = 'build_failed') OR (status = 'aborted') OR (status = 'terminated'))
			);
			""")

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""\
			CREATE TABLE testcollection_testcases (
				collection_id integer NOT NULL REFERENCES testcollection(collection_id),
				tc_id integer NOT NULL REFERENCES testcases(tc_id),
				UNIQUE(collection_id, tc_id)
			);
			""")

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""\
			CREATE TABLE testresult (
				tc_id integer REFERENCES testcases(tc_id),
				run_id integer REFERENCES testrun(run_id),
				received_reply varchar(4096) NULL,
				status varchar(32) NOT NULL DEFAULT 'no_answer',
				UNIQUE(tc_id, run_id),
				CHECK((status = 'no_answer') OR (status = 'pass') OR (status = 'fail') OR (status = 'indeterminate'))
			);
			""")

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("CREATE index testresult_run_id_idx ON testresult(run_id);")

	def create_testcase(self, action: str, arguments: dict, created_utcts: datetime.datetime, correct_reply: dict | None = None, dependencies: dict | None = None):
		self._insert("testcases", {
			"action": action,
			"arguments": arguments,
			"created_utcts": created_utcts,
			"correct_reply": correct_reply,
			"dependencies": dependencies,
		})

	def create_testrun(self, submission: "Submission", testcases: "TestcaseCollection"):
		run_id = self._insert("testrun", {
			"source": submission.shortname,
			"source_metadata": submission.to_dict(),
			"run_start_utcts": datetime.datetime.now(datetime.UTC),
			"max_permissible_runtime_secs": 999999,		# TODO
			"max_permissible_ram_mib": 999999,		# TODO
			"dependencies": testcases.dependencies,
			"status": TestrunStatus.Running,
			"collection": testcases.name,
		})
		for testcase in testcases:
			self._insert("testresult", {
				"tc_id":	testcase.tc_id,
				"run_id":	run_id,
			})
		return run_id

	def update_testresult(self, run_id: int, tc_id: int, received_reply: dict, test_result_status: TestresultStatus):
		self._mapped_execute("UPDATE testresult SET received_reply = ?, status = ? WHERE (tc_id = ?) AND (run_id = ?);",
							(received_reply, "testresult:received_reply"),
							(test_result_status, "testresult:status"),
							tc_id, run_id)
		self._increase_uncommitted_write_count()

	def close_testrun(self, run_id: int, submission_run_result: "SubmissionRunResult"):
		self._mapped_execute("UPDATE testrun SET status = ?, error_details = ?, run_end_utcts = ?, stderr = ? WHERE run_id = ?;",
							(submission_run_result.testrun_status, "testrun:status"),
							(submission_run_result.error_details, "testrun:error_details"),
							(datetime.datetime.now(datetime.UTC), "testrun:run_end_utcts"),
							submission_run_result.stderr,
							run_id)
		self._increase_uncommitted_write_count()

	def _get_tc_ids_for_selector_part(self, testcase_selector_part: str):
		if testcase_selector_part.isdigit():
			return set([ int(testcase_selector_part) ])
		elif testcase_selector_part == "*":
			return set(row["tc_id"] for row in self._cursor.execute("SELECT tc_id FROM testcases;").fetchall())
		elif testcase_selector_part.startswith("@"):
			action = testcase_selector_part[1:]
			return set(row["tc_id"] for row in self._cursor.execute("SELECT tc_id FROM testcases WHERE action = ?;", (action, )).fetchall())
		else:
			raise NoSuchCollectionException(f"Invalid testcase selector: {testcase_selector_part}")

	def get_tc_ids_by_selector(self, testcase_selector: str) -> set[int]:
		tc_ids = set()
		for testcase_selector_part in [ part.strip() for part in testcase_selector.split(",") ]:
			tc_ids |= self._get_tc_ids_for_selector_part(testcase_selector_part)
		return tc_ids

	def _get_testcase(self, tc_id: int, contained_collections: set | None = None) -> Testcase:
		row = dict(self._cursor.execute("SELECT action, arguments, correct_reply, dependencies FROM testcases WHERE tc_id = ?;", (tc_id, )).fetchone())
		for key in [ "arguments", "correct_reply", "dependencies" ]:
			if row[key] is not None:
				row[key] = json.loads(row[key])
		row["tc_id"] = tc_id
		row["contained_collections"] = contained_collections
		return Testcase(**row)

	def _get_collection_id(self, collection_name: str) -> int:
		collection_id = self._cursor.execute("SELECT collection_id FROM testcollection WHERE name = ? LIMIT 1 COLLATE NOCASE;", (collection_name, )).fetchone()
		if collection_id is None:
			raise NoSuchCollectionException(f"No such test case collection: {collection_name}")
		return collection_id["collection_id"]

	def add_tc_ids_to_collection(self, collection_name: str, tc_ids: set[int]) -> None:
		collection_id = self._get_collection_id(collection_name)
		for tc_id in tc_ids:
			with contextlib.suppress(sqlite3.IntegrityError):
				self._insert("testcollection_testcases", {
					"collection_id": collection_id,
					"tc_id": tc_id,
				})

	def remove_tc_ids_from_collection(self, collection_name: str, tc_ids: set[int]) -> None:
		collection_id = self._get_collection_id(collection_name)
		for tc_id in tc_ids:
			self._cursor.execute("DELETE FROM testcollection_testcases WHERE (collection_id = ?) AND (tc_id = ?);", (collection_id, tc_id))

	def get_testcase_collection(self, collection_name: str) -> TestcaseCollection:
		collection_id = self._get_collection_id(collection_name)
		row = self._cursor.execute("SELECT name, reference_runtime_secs FROM testcollection WHERE collection_id = ?;", (collection_id, )).fetchone()
		tc_ids = set(row["tc_id"] for row in self._cursor.execute("SELECT tc_id FROM testcollection_testcases WHERE collection_id = ?;", (collection_id, )).fetchall())
		testcases = [ self._get_testcase(tc_id) for tc_id in tc_ids ]
		return TestcaseCollection(name = row["name"], testcases = testcases, reference_runtime_secs = row["reference_runtime_secs"])

	def create_collection(self, collection_name: str):
		self._increase_uncommitted_write_count()
		return self._cursor.execute("INSERT INTO testcollection (collection_id, name) VALUES ((SELECT COALESCE(MAX(collection_id) + 1, 1) FROM testcollection), ?);", (collection_name, )).lastrowid

	def get_all_testcases(self) -> iter:
		tags = ((row["tc_id"], row["name"]) for row in self._cursor.execute("""\
				SELECT tc_id, name FROM testcollection_testcases
					JOIN testcollection ON testcollection.collection_id = testcollection_testcases.collection_id;
					""").fetchall())

		contained_collections = collections.defaultdict(set)
		for (tc_id, collection_name) in tags:
			contained_collections[tc_id].add(collection_name)

		for row in self._cursor.execute("SELECT tc_id FROM testcases;").fetchall():
			testcase = self._get_testcase(row["tc_id"], contained_collections = contained_collections[row["tc_id"]])
			yield testcase

	def get_latest_run_id(self, collection_name: str, submission_name: str) -> int | None:
		row = self._cursor.execute("SELECT run_id FROM testrun WHERE collection = ? AND source = ? ORDER BY run_id DESC LIMIT 1;", (collection_name, submission_name)).fetchone()
		if row is None:
			return None
		return row["run_id"]

	def get_latest_run_ids(self, max_list_length: int = 10) -> list[int]:
		return [ row["run_id"] for row in self._cursor.execute("SELECT run_id FROM testrun ORDER BY run_start_utcts DESC LIMIT ?;", (max_list_length, )).fetchall() ]

	def get_run_overview(self, run_id: int, full_overview: bool = False):
		row = self._mapped_execute(f"""
			SELECT {'*' if full_overview else 'run_id, collection, source, source_metadata, run_start_utcts, run_end_utcts, max_permissible_runtime_secs, max_permissible_ram_mib, status, error_details'} FROM testrun
			WHERE run_id = ?;
		""", run_id)._mapped_fetchone("testrun")
		return row

	def get_run_result_count(self, run_id: int):
		return [ (TestresultStatus(row["status"]), row["count"]) for row in self._cursor.execute("""
			SELECT testresult.status, COUNT(testrun.run_id) AS count FROM testrun
			JOIN testresult ON testrun.run_id = testresult.run_id
			WHERE testrun.run_id = ?
			GROUP BY testrun.run_id, testresult.status
			ORDER BY count DESC;
		""", (run_id, )).fetchall() ]

	def get_run_details(self, run_id: int):
		return self._mapped_execute("""
			SELECT testcases.tc_id, testcases.action, testcases.arguments, testcases.correct_reply, received_reply, status FROM testresult
				JOIN testcases ON testcases.tc_id = testresult.tc_id
				WHERE run_id = ?;
			""", run_id)._mapped_fetchall("testcases", "testresult")

	def set_reference_runtime(self, collection_name: str, runtime_secs: float):
		self._cursor.execute("UPDATE testcollection SET reference_runtime_secs = ? WHERE name = ?;", (runtime_secs, collection_name))
		self._increase_uncommitted_write_count()

	def set_reference_answer(self, tc_id: int, correct_reply: dict):
		self._mapped_execute("UPDATE testcases SET correct_reply = ? WHERE tc_id = ?;",
					(correct_reply, "testcases:correct_reply"),
					tc_id)
		self._increase_uncommitted_write_count()
