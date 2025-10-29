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

from .CmdlineAction import CmdlineAction

class ActionLeaderboard(CmdlineAction):
	def run(self):
		collection = self._db.get_testcase_collection(self._args.collection_name)

		leaderboard = self._db.get_leaderboard(self._args.collection_name)
		print(f"Best runs for collection {self._args.collection_name} with all pass results, reftime {collection.reference_runtime_secs:.2f} sec")
		for entry in leaderboard:
			print(f"{entry['source']:<15s}   {entry['run_id']:5d}   {entry['min_runtime_secs']:>8.2f} sec    {entry['min_runtime_secs'] / collection.reference_runtime_secs * 100:>6.1f}% of ref" )
