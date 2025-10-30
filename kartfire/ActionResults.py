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
from .ResultPrinter import ResultPrinter
from .ResultHTMLGenerator import ResultHTMLGenerator
from .RunResult import MultiRunResult

class ActionResults(CmdlineAction):
	def _print_summary_by_run(self):
		for run_id in self._db.get_latest_run_ids(50):
			run_result = MultiRunResult.load_single_run(self._db, run_id)
			self._result_printer.print_run_overview(run_result)

	def _print_summary_by_multirun(self):
		for multirun_id in self._db.get_latest_multirun_ids(50):
			multirun = MultiRunResult(self._db, multirun_id)
			self._result_printer.print_multirun_overview(multirun)

	def _print_run(self, run_id: int):
		self._result_printer.print_details(run_id)

	def run(self):
		self._result_printer = ResultPrinter(self._db)
		if self._args.html_template is None:
			if len(self._args.run_id) == 0:
				if self._args.summary_by_run:
					self._print_summary_by_run()
				else:
					self._print_summary_by_multirun()
			else:
				for run_id in self._args.run_id:
					self._print_run(run_id)
		else:
			html_generator = ResultHTMLGenerator(self._db)
			result = html_generator.create(run_ids = self._args.run_id, template_name = self._args.html_template)
			print(result)
