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
import collections
from .CmdlineAction import CmdlineAction

class ActionReference(CmdlineAction):
	def run(self):
		run_details = self._db.get_run_details(self._args.run_id)

		ctr = collections.Counter(result["status"] for result in run_details["results"])
		print(ctr)
		print(len(ctr))

		if len(ctr) == 0:
			print("No answers received.")
			return 1

		if len(ctr) != 1:
			print("Have multiple statuses:")
			for (status, count) in ctr.most_common():
				print(f"{status:<30s} {count}")
			TODO

		for result in run_details["results"]:
			if (result["status"] == "indeterminate") or ((result["status"] == "fail") and self._args.pick_failed_answers):
				self._db.set_reference_answer(result["testcase"].tcid, json.loads(result["received_result"]))
				self._db.opportunistic_commit()
		self._db.commit()
