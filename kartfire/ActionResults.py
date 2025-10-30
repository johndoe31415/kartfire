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

import mailcoil
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
					yield MultiRunResult.load_single_run(self._db, int_value)

				case "multirun_id":
					yield MultiRunResult(self._db, int_value)

				case _:
					raise NotImplementedError(runtype)

	def run(self):
		self._multiruns = list(self._load_multiruns())
		self._result_printer = ResultPrinter(self._db)
		if self._args.html_template is None:
			if len(self._multiruns) == 0:
				if self._args.summary_by_run:
					self._print_summary_by_run()
				else:
					self._print_summary_by_multirun()
			else:
				for multirun in self._multiruns:
					self._result_printer.print_details(multirun)
		else:
			html_generator = ResultHTMLGenerator(self._db)
			for multirun in self._multiruns:
				result = html_generator.create(multirun = multirun, template_name = self._args.html_template)
				print(result)

		if self._args.send_email:
			dropoff = mailcoil.MailDropoff.parse_uri(self._test_fixture_config.email_via_uri)

			html_generator = ResultHTMLGenerator(self._db)
			for multirun in self._multiruns:
				email_body = html_generator.create(multirun = multirun, template_name = "email.html")

				if multirun.solution_email is None:
					print(f"Unable to send email, email field not populated: {multirun}")
					continue

				if multirun.solution_author is None:
					to_address = mailcoil.MailAddress(mail = multirun.solution_email)
				else:
					to_address = mailcoil.MailAddress(name = multirun.solution_author, mail = multirun.solution_email)

				print(f"Sending results of {multirun} to {to_address}")
				subject = f"Ergebnis der Kartfire CI/CD"
				mail = mailcoil.Email(from_address = mailcoil.MailAddress.parse(self._test_fixture_config.email_from), subject = subject).to(to_address)
				mail.html = email_body
				dropoff.post(mail)
#			print(email_body)
