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
from .CmdlineAction import CmdlineAction

class ActionImport(CmdlineAction):
	def _import(self, filename: str):
		duplicate_skipped_count = 0
		imported_count = 0
		now = datetime.datetime.now(datetime.UTC)
		with open(filename) as f:
			testcases = json.load(f)
		for testcase in testcases:
			try:
				self._db.create_testcase(action = testcase["action"], query = testcase["query"], created_ts = now, correct_response = testcase.get("correct_response"), dependencies = testcase.get("dependencies"), reference_runtime_secs = testcase.get("reference_runtime_secs"))
				imported_count += 1
			except sqlite3.IntegrityError:
				duplicate_skipped_count += 1
			self._db.opportunistic_commit()
		self._db.commit()
		print(f"{filename}: imported {imported_count}, skipped {duplicate_skipped_count} duplicate testcases")

	def run(self):
		for filename in self._args.testcase_filename:
			self._import(filename)
