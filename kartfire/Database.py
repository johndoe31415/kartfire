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
import kartfire
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

		self._map_type("multirun:source_metadata", "json")
		self._map_type("multirun:environment_metadata", "json")
		self._map_type("multirun:build_start_utcts", "utcts")
		self._map_type("multirun:build_end_utcts", "utcts")
		self._map_type("multirun:build_status", "enum", TestrunStatus)
		self._map_type("multirun:build_error_details", "json")

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

		# A multirun consists of an (optinal) build step and possible many
		# testruns (each with their own collections)
		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""\
			CREATE TABLE multirun (
				multirun_id integer PRIMARY KEY,
				source varchar(256) NOT NULL,
				source_metadata varchar(4096) NOT NULL,
				environment_metadata varchar(4096) NOT NULL,
				build_start_utcts varchar(64) NOT NULL,
				build_end_utcts varchar(64) NULL,
				total_time_secs float NULL,									-- total time for the whole run, including running of all testruns, i.e., from build_start_utcts to the last testrun.run_end_utcts
				build_status varchar(32) NOT NULL DEFAULT 'running',
				build_stdout blob NULL,
				build_stderr blob NULL,
				build_runtime_secs float NULL,								-- pure runtime of the build script; for output relative to the user
				build_runtime_allowance_secs float NULL,
				build_error_details varchar(4096) NULL,
				CHECK((build_status = 'running') OR (build_status = 'finished') OR (build_status = 'failed') OR (build_status = 'aborted') OR (build_status = 'terminated'))
			);
			""")

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""\
			CREATE TABLE testrun (
				run_id integer PRIMARY KEY,
				multirun_id integer NOT NULL REFERENCES multiruns(multirun_id),
				collection varchar(128) NOT NULL REFERENCES testcollection(name),
				run_start_utcts varchar(64) NOT NULL,
				run_end_utcts varchar(64) NULL,
				runtime_secs float NULL,						-- pure runtime of the run testcase script; for output relative to the user
				testcase_count integer NOT NULL,				-- total amount of associated testcases with this run
				runtime_allowance_secs float NULL,
				max_permissible_ram_mib integer NOT NULL,
				dependencies varchar(4096) NOT NULL,
				status varchar(32) NOT NULL DEFAULT 'running',
				error_details varchar(4096) NULL,
				stderr blob NULL,
				CHECK((status = 'running') OR (status = 'finished') OR (status = 'failed') OR (status = 'aborted') OR (status = 'terminated'))
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
				tc_id integer NOT NULL REFERENCES testcases(tc_id),
				run_id integer NOT NULL REFERENCES testrun(run_id),
				received_reply varchar(4096) NULL,
				status varchar(32) NOT NULL DEFAULT 'no_answer',
				UNIQUE(tc_id, run_id),
				CHECK((status = 'no_answer') OR (status = 'pass') OR (status = 'fail') OR (status = 'indeterminate'))
			);
			""")

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("CREATE index testresult_run_id_idx ON testresult(run_id);")

		with contextlib.suppress(sqlite3.OperationalError):
			self._cursor.execute("""CREATE VIEW successful_runs_runtimes AS
				SELECT run_id, source, collection, runtime_secs FROM
					(SELECT testrun.run_id, multirun.source, collection, COUNT(testresult.status) AS passed_count, testcase_count, runtime_secs FROM testrun
						JOIN multirun ON multirun.multirun_id = testrun.multirun_id
						JOIN testresult ON testresult.run_id = testrun.run_id
						WHERE (testrun.status = 'finished') AND (testresult.status = 'pass')
						GROUP BY testrun.run_id)
				WHERE passed_count = testcase_count;
			""")


	def create_testcase(self, action: str, arguments: dict, created_utcts: datetime.datetime, correct_reply: dict | None = None, dependencies: dict | None = None):
		self._insert("testcases", {
			"action": action,
			"arguments": arguments,
			"created_utcts": created_utcts,
			"correct_reply": correct_reply,
			"dependencies": dependencies,
		})

	def create_multirun(self, submission: "Submission", build_constraints: "RunConstraints", container_image_metadata: "ContainerImageMetadata"):
		env = {
			"kartfire": kartfire.VERSION,
			"image": container_image_metadata.to_dict(),
		}
		multirun_id = self._insert("multirun", {
			"source": submission.shortname,
			"source_metadata": submission.to_dict(),
			"environment_metadata": env,
			"build_start_utcts": datetime.datetime.now(datetime.UTC),
			"build_status": TestrunStatus.Running,
			"build_runtime_allowance_secs": build_constraints.runtime_allowance_secs,
		})
		return multirun_id

	def update_multirun_build_status(self, multirun_id: int, exec_result: "ExecutionResult"):
		self._mapped_execute("UPDATE multirun SET build_end_utcts = ?, build_status = ?, build_stdout = ?, build_stderr = ?, build_runtime_secs = ?, build_error_details = ? WHERE (multirun_id = ?);",
								(datetime.datetime.now(datetime.UTC), "multirun:build_end_utcts"),
								(exec_result.testrun_status, "multirun:build_status"),
								exec_result.stdout,
								exec_result.stderr,
								exec_result.runtime_secs,
							   (exec_result.error_details, "multirun:build_error_details"),
								multirun_id)
		self._increase_uncommitted_write_count()

	def create_testrun(self, multirun_id: int, testcase_collection: "TestcaseCollection", run_constraints: "RunConstraints"):
		run_id = self._insert("testrun", {
			"multirun_id": multirun_id,
			"run_start_utcts": datetime.datetime.now(datetime.UTC),
			"testcase_count": len(testcase_collection),
			"runtime_allowance_secs": run_constraints.runtime_allowance_secs,
			"max_permissible_ram_mib": run_constraints.max_permissible_ram_mib,
			"dependencies": testcase_collection.dependencies,
			"status": TestrunStatus.Running,
			"collection": testcase_collection.name,
		})
		for testcase in testcase_collection:
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

	def close_testrun(self, run_id: int, exec_result: "ExecutionResult"):
		now = datetime.datetime.now(datetime.UTC)
		self._mapped_execute("UPDATE testrun SET status = ?, error_details = ?, run_end_utcts = ?, runtime_secs = ?, stderr = ? WHERE run_id = ?;",
							(exec_result.testrun_status, "testrun:status"),
							(exec_result.error_details, "testrun:error_details"),
							(now, "testrun:run_end_utcts"),
							exec_result.runtime_secs,
							exec_result.stderr,
							run_id)
		self._increase_uncommitted_write_count()

	def close_multirun(self, multirun_id: int):
		now = datetime.datetime.now(datetime.UTC)
		start_ts = self._mapped_execute("SELECT build_start_utcts FROM multirun WHERE multirun_id = ?;", multirun_id)._mapped_fetchone("multirun")["build_start_utcts"]
		total_time_secs = (now - start_ts).total_seconds()
		self._cursor.execute("UPDATE multirun SET total_time_secs = ? WHERE multirun_id = ?;", (total_time_secs, multirun_id))
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

	def get_latest_multirun_id(self, submission_name: str) -> int | None:
		row = self._cursor.execute("SELECT multirun_id FROM multirun WHERE source = ? ORDER BY multirun_id DESC LIMIT 1;", (submission_name, )).fetchone()
		if row is None:
			return None
		return row["multirun_id"]

	def get_latest_run_ids(self, max_list_length: int = 10) -> list[int]:
		return [ row["run_id"] for row in self._cursor.execute("SELECT run_id FROM testrun ORDER BY run_start_utcts DESC LIMIT ?;", (max_list_length, )).fetchall() ]

	def get_latest_multirun_ids(self, max_list_length: int = 10) -> list[int]:
		return [ row["multirun_id"] for row in self._cursor.execute("SELECT multirun_id FROM multirun ORDER BY build_start_utcts DESC LIMIT ?;", (max_list_length, )).fetchall() ]

	def get_multirun_overview(self, multirun_id: int):
		row = self._mapped_execute("""
			SELECT multirun_id, source, source_metadata, environment_metadata, build_start_utcts, build_end_utcts, build_runtime_secs, build_runtime_allowance_secs, build_status, build_error_details FROM multirun
				WHERE multirun_id = ?;
		""", multirun_id)._mapped_fetchone("multirun")
		return row

	def get_run_overview(self, run_id: int, full_overview: bool = False):
		row = self._mapped_execute(f"""
			SELECT {'testrun.*' if full_overview else 'run_id, multirun_id, collection, run_start_utcts, run_end_utcts, runtime_secs, testcase_count, runtime_allowance_secs, max_permissible_ram_mib, status, error_details'}, testcollection.reference_runtime_secs FROM testrun
				LEFT JOIN testcollection ON testcollection.name = testrun.collection
				WHERE run_id = ?;
		""", run_id)._mapped_fetchone("testrun")
		return row

	def get_run_overviews_of_multirun(self, multirun_id: int):
		return self._mapped_execute("""
			SELECT run_id, multirun_id, collection, run_start_utcts, run_end_utcts, runtime_secs, testcase_count, runtime_allowance_secs, max_permissible_ram_mib, status, error_details, testcollection.reference_runtime_secs FROM testrun
				LEFT JOIN testcollection ON testcollection.name = testrun.collection
				WHERE multirun_id = ?
				ORDER BY run_id ASC;
		""", multirun_id)._mapped_fetchall("testrun")

	def get_run_result_count(self, run_id: int):
		return [ (TestresultStatus(row["status"]), row["count"]) for row in self._cursor.execute("""
			SELECT status, COUNT(run_id) AS count FROM testresult
			WHERE run_id = ?
			GROUP BY status
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

	def get_leaderboard(self, collection_name: str):
		return self._mapped_execute("""
			SELECT MIN(run_id) AS run_id, source, min_runtime_secs FROM
				(SELECT run_id, source, collection, runtime_secs, MIN(runtime_secs) OVER (PARTITION BY source, collection) AS min_runtime_secs FROM successful_runs_runtimes) AS subqry
				WHERE (runtime_secs = min_runtime_secs) AND (collection = ?)
				GROUP BY source, collection, min_runtime_secs
				ORDER BY min_runtime_secs ASC
			;
		""", collection_name)._mapped_fetchall()
