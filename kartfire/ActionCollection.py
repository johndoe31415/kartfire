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

import contextlib
from .Exceptions import NoSuchCollectionException
from .CmdlineAction import CmdlineAction

class ActionCollection(CmdlineAction):
	def run(self):
		collection = None
		with contextlib.suppress(NoSuchCollectionException):
			collection = self._db.get_testcase_collection(self._args.collection_name)

		if collection is None:
			if  (not self._args.remove) and (self._args.testcase_selector is not None):
				# Collection does not exist, but we want to add entries, create it.
				self._db.create_collection(self._args.collection_name)
			else:
				print(f"No such collection: {self._args.collection_name}")
				return

		if (self._args.testcase_selector is not None):
			tc_ids = self._db.get_tc_ids_by_selector(self._args.testcase_selector)
			if len(tc_ids) > 0:
				if self._args.remove:
					self._db.remove_tc_ids_from_collection(self._args.collection_name, tc_ids)
				else:
					self._db.add_tc_ids_to_collection(self._args.collection_name, tc_ids)
			collection = self._db.get_testcase_collection(self._args.collection_name)

		self._db.commit()
		print(collection)
