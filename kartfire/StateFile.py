#	kartfire - Test framework to consistently run submission files
#	Copyright (C) 2023-2024 Johannes Bauer
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

import os
import json
import datetime
from .Tools import GitTools

class StateFile():
	def __init__(self, filename: str):
		self._filename = filename
		try:
			with open(self._filename) as f:
				self._state = json.load(f)
		except (FileNotFoundError, json.decoder.JSONDecodeError):
			self._state = { }

	def need_to_run(self, path: str):
		path = os.path.realpath(path)
		git = GitTools.gitinfo(path)
		if git is None:
			# No Git repo?
			return

		if "commit" not in git:
			# We don't have a commit checked out, ignore directory.
			return False

		commit = git["commit"]
		if self._state.get(path, { }).get("commit") == commit:
			# Already handeled this
			return False

		# Run it.
		self._state[path] = {
			"last_run": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
			"commit": commit,
		}
		return True

	def write(self):
		with open(self._filename, "w") as f:
			json.dump(self._state, f)
