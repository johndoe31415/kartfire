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

import os
import json
from .CmdlineAction import CmdlineAction

class ActionAlias(CmdlineAction):
	def _import(self, filename: str):
		with open(filename) as f:
			source = os.path.splitext(os.path.basename(filename))[0]
			metadata = json.load(f)
			kartfire_metadata = metadata.get("kartfire", { })
			if "leaderboard_name" in kartfire_metadata:
				self._db.leaderboard_alias_add(source, kartfire_metadata["leaderboard_name"])

	def run(self):
		if self._args.remove_all_aliases:
			self._db.leaderboard_aliases_remove()
		for filename in self._args.metadata_filename:
			self._import(filename)
		self._db.commit()
