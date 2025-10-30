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

import time
import json
import datetime
import sqlite3

class DebuggingCursor():
	def __init__(self, cursor):
		self._cursor = cursor

	def execute(self, sql_query: str, arguments: tuple | None = ()):
		t0 = time.time()
		result = self._cursor.execute(sql_query, arguments)
		t = time.time() - t0
		print(f"{1000 * t:.0f} {sql_query}")
		return result

	def __getattr__(self, attr_name: str):
		return getattr(self._cursor, attr_name)


class SqliteORM():
	def __init__(self, filename: str):
		self._conn = sqlite3.connect(filename)
		self._conn.row_factory = sqlite3.Row
#		self._cursor = DebuggingCursor(self._conn.cursor())
		self._cursor = self._conn.cursor()
		self._uncommitted_write_count = 0
		self._max_uncommitted_writes = 100
		self._known_types = { }
		self._types = { }

	def _map_type(self, name: str, type_name: str, *type_args: any):
		self._types[name] = (type_name, ) + type_args

	def _map_py_to_db_value(self, value: any, type_name: str):
		if type_name not in self._types:
			# No mapping occurs
			return value

		match self._types[type_name]:
			case ("enum", enum_class):
				assert(isinstance(value, enum_class))
				return value.value

			case ("json", ):
				return json.dumps(value, sort_keys = True, separators = (",", ":"))

			case ("utcts", ):
				assert(isinstance(value, datetime.datetime))
				assert(value.tzinfo == datetime.timezone.utc)
				return value.isoformat()[:-6] + "Z"

			case _:
				raise ValueError(f"Unknown type descriptor: {self._types[type_name]}")

	def _map_db_to_py_value(self, value: any, type_name: str):
		if (value is None) or (type_name not in self._types):
			# No mapping occurs
			return value

		match self._types[type_name]:
			case ("enum", enum_class):
				return enum_class(value)

			case ("json", ):
				return json.loads(value)

			case ("utcts", ):
				return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo = datetime.UTC)

			case _:
				raise ValueError(f"Unknown type descriptor: {self._types[type_name]}")

	def _map_py_to_db(self, *parameters: tuple[any]) -> tuple[any]:
		def _map(parameter):
			if isinstance(parameter, tuple):
				type_name = parameter[1]
				assert(type_name in self._types)
				return self._map_py_to_db_value(parameter[0], type_name)
			else:
				return parameter
		return tuple(_map(parameter) for parameter in parameters)

	def _map_db_to_py(self, row: sqlite3.Row, *table_names: tuple[str]):
		result = { }
		for (key, value) in dict(row).items():
			for table_name in table_names:
				type_name = f"{table_name}:{key}"
				if type_name in self._types:
					value = self._map_db_to_py_value(value, type_name)
					break
			result[key] = value
		return result

	def _insert(self, table_name: str, values: dict):
		mapped_values = { key: self._map_py_to_db_value(value, type_name = f"{table_name}:{key}") for (key, value) in values.items() }
		fields = list(mapped_values)
		values = [ mapped_values[field] for field in fields ]
		query = f"INSERT INTO {table_name} ({','.join(field for field in fields)}) VALUES ({','.join([ '?' ] * len(fields))});"
		result = self._cursor.execute(query, values)
		self._uncommitted_write_count += 1
		return result.lastrowid

	def _mapped_execute(self, query: str, *parameters: tuple[any]):
		self._cursor.execute(query, self._map_py_to_db(*parameters))
		return self

	def _mapped_fetchone(self, *table_names: tuple[str]):
		return self._map_db_to_py(self._cursor.fetchone(), *table_names)

	def _mapped_fetchall(self, *table_names: tuple[str]):
		return [ self._map_db_to_py(row, *table_names) for row in self._cursor.fetchall() ]

	def _increase_uncommitted_write_count(self):
		self._uncommitted_write_count += 1

	def opportunistic_commit(self):
		if self._uncommitted_write_count > self._max_uncommitted_writes:
			self.commit()

	def commit(self):
		self._conn.commit()
		self._uncommitted_write_count = 0

if __name__ == "__main__":
	import enum
	import contextlib

	class MyNum(enum.Enum):
		Foo = "foo!"
		Bar = "bar!"

	class TestDB(SqliteORM):
		def __init__(self, filename: str):
			super().__init__(filename)
			with contextlib.suppress(sqlite3.OperationalError):
				self._cursor.execute("""CREATE TABLE foo (
					id integer PRIMARY KEY,
					foo_json varchar(1024),
					created ts,
					num varchar(64)
				);""")

	testdb = TestDB("testdb.sqlite3")
	testdb._map_type("foo:foo_json", "json")
	testdb._map_type("foo:created", "utcts")
	testdb._map_type("foo:num", "enum", MyNum)
	testdb._insert("foo", {
		"foo_json": { "foo": 9, "bar": 23748 },
		"created": datetime.datetime.now(datetime.UTC),
		"num": MyNum.Foo,
	})
	testdb.commit()

	for row in testdb._cursor.execute("SELECT * FROM foo;").fetchall():
		print(testdb._map_db_to_py(row, "foo"))
