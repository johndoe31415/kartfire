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
from .Enums import TestrunStatus
from .CmdlineAction import CmdlineAction
from .ResultPrinter import ResultPrinter

class ActionResults(CmdlineAction):
	def _print_summary(self):
		for runid in self._db.get_latest_runids():
			self._result_printer.print_overview(runid)

	def _print_run(self, runid: int):
		pass

	def run(self):
		self._result_printer = ResultPrinter(self._db)
		if len(self._args.run_id) == 0:
			self._print_summary()
		else:
			for runid in self._args.run_id:
				self._print_run(runid)
