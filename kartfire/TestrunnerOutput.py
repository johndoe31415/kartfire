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

import json
from .Enums import TestrunStatus

class TestrunnerOutput():
	def __init__(self):
		self._status = TestrunStatus.Skipped
		self._stdout = None
		self._stderr = None
		self._parsed = None

	@property
	def testcase_count(self):
		if self._parsed is not None:
			return len(self._parsed["testcase_results"])
		else:
			return 0

	@property
	def status(self):
		return self._status

	@status.setter
	def status(self, value: TestrunStatus):
		self._status = value

	@property
	def logs(self):
		return (self._stdout, self._stderr)

	@logs.setter
	def logs(self, value: tuple[bytes]):
		(self._stdout, self._stderr) = value
		try:
			self._parsed = json.loads(self._stdout)
		except json.decoder.JSONDecodeError:
			self.status = TestrunStatus.ErrorUnparsable

	def dump(self, verbose = False):
		print(self)
		print(self._stdout.decode("ascii", errors = "ignore"))
		print("=" * 120)
		print(self._stderr.decode("ascii", errors = "ignore"))

	def __iter__(self):
		if self._parsed is not None:
			return iter(self._parsed["testcase_results"])

	def __repr__(self):
		return f"TestrunnerOutput<{self.status.name}>"
