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
from .RunResult import MultiRunResult
from .Enums import TestresultStatus

class ActionReference(CmdlineAction):
	def run(self):
		multirun_id = self._db.get_latest_multirun_id(submission_name = self._args.submission_name)
		if multirun_id is None:
			print(f"No solution for submission {self._args.submission_name} found.")
			return 1

		multirun_result = MultiRunResult(self._db, multirun_id)
		for run_result in multirun_result:
			if not run_result.have_results:
				print(f"Cannot apply run id {run_result.run_id} as reference: no answers present in solution.")
				return 1

			if len(run_result.result_count) != 1:
				print("Have multiple statuses:")
				for (status, count) in run_result.result_count:
					print(f"{status:<30s} {count}")

			self._db.set_reference_runtime(run_result.collection_name, run_result.runtime.duration_secs)
			for result in run_result.testresult_details:
				if (result["status"] == TestresultStatus.Indeterminate) or ((result["status"] == TestresultStatus.Fail) and self._args.pick_failed_answers):
					self._db.set_reference_answer(result["tc_id"], result["received_reply"])
					self._db.opportunistic_commit()
		self._db.commit()
		return 0
