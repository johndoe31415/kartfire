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

import sys
import mailcoil
from .Exceptions import NoSuchMultirunException
from .CmdlineAction import CmdlineAction
from .ResultPrinter import ResultPrinter
from .ResultHTMLGenerator import ResultHTMLGenerator
from .RunResult import MultiRunResult

class ActionResults(CmdlineAction):
	@classmethod
	def id_type(cls, text: str):
		if text.startswith("m"):
			return ("multirun_id", int(text[1:]))
		else:
			return ("run_id", int(text))

	def _print_summary_by_run(self):
		for run_id in self._db.get_latest_run_ids(50):
			run_result = MultiRunResult.load_single_run(self._db, run_id)
			self._result_printer.print_run_overview(run_result)

	def _print_summary_by_multirun(self):
		for multirun_id in self._db.get_latest_multirun_ids(50):
			multirun = MultiRunResult(self._db, multirun_id)
			self._result_printer.print_multirun_overview(multirun)

	def _load_multiruns(self):
		for (runtype, int_value) in self._args.run_multirun_id:
			match runtype:
				case "run_id":
					yield MultiRunResult.load_single_run(self._db, int_value).multirun

				case "multirun_id":
					try:
						yield MultiRunResult(self._db, int_value)
					except NoSuchMultirunException:
						print(f"Ignoring non-existent multirun {int_value}", file = sys.stderr)

				case _:
					raise NotImplementedError(runtype)

	def _print_multiruns(self, multirun_list: list[MultiRunResult]):
		for multirun_result in multirun_list:
			if self._args.detail_level == 0:
				self._result_printer.print_multirun_overview(multirun_result)
			else:
				self._result_printer.print_details(multirun_result)

	def _show_runs(self):
		raise NotImplementedError()

	def _show_multiruns(self):
		raise NotImplementedError()

	def _show_solutions(self):
		results = self._db.get_most_recent_multirun_by_source(filter_source = self._args.filter_source, filter_submitter_name = self._args.filter_submitter_name, limit = self._args.limit)
		multiruns = [ ]
		for result in results:
			multiruns.append(MultiRunResult(self._db, result["multirun_id"]))
		self._print_multiruns(multiruns)

	def run(self):
		self._result_printer = ResultPrinter(self._db)
		handler = getattr(self, f"_show_{self._args.show.replace('-', '_')}")
		return handler()
#		self._multiruns = list(self._load_multiruns())





#		if self._args.html_template is None:
#			if len(self._args.run_multirun_id) == 0:
#				if self._args.summary_by_run:
#					self._print_summary_by_run()
#				else:
#					self._print_summary_by_multirun()
#			else:
#				for multirun in self._multiruns:
#					self._result_printer.print_details(multirun)
#		else:
#			html_generator = ResultHTMLGenerator(self._db)
#			for multirun in self._multiruns:
#				result = html_generator.create(multirun = multirun, template_name = self._args.html_template)
#				print(result)
#
#		if self._args.send_email:
#			html_generator = ResultHTMLGenerator(self._db)
#			dropoff = mailcoil.MailDropoff.parse_uri(self._test_fixture_config.email_via_uri)
#			for multirun in self._multiruns:
#				multirun.send_email(test_fixture_config = self._test_fixture_config, html_generator = html_generator, dropoff = dropoff)
