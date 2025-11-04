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

import json
import sqlite3
import datetime
import time
from .CmdlineAction import CmdlineAction

class ActionImport(CmdlineAction):
	def _import(self, filename: str):
		now = datetime.datetime.now(datetime.UTC)
		with open(filename) as f:
			testcases = json.load(f)
		print(f"{filename}: importing {len(testcases)} testcases")
		testcase_data = [ {
				"action": testcase["action"],
				"arguments": testcase["arguments"],
				"created_utcts": now,
				"correct_reply": testcase.get("correct_reply"),
				"dependencies": testcase.get("dependencies")
			} for testcase in testcases ]
		self._db._insert_many("testcases", testcase_data, ignore_duplicate = True)
		self._db.commit()

	def run(self):
		for filename in self._args.testcase_filename:
			self._import(filename)
