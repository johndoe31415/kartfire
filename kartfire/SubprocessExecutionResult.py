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
import base64
import functools
from .Enums import ExecutionResult

class SubprocessExecutionResult():
	def __init__(self, result_dict: dict):
		self._result_dict = result_dict
		self._have_stdout_json = None

	@property
	def runtime_secs(self) -> float:
		return self._result_dict["runtime_secs"]

	@property
	def returncode(self) -> int | None:
		return self._result_dict.get("returncode")

	@property
	def exception_msg(self) -> str | None:
		return self._result_dict.get("exception_msg")

	@property
	def runtime_limit_secs(self) -> float:
		return self._result_dict["runtime_limit_secs"]

	@functools.cached_property
	def stdout(self):
		if "stdout" in self._result_dict:
			return base64.b64decode(self._result_dict["stdout"]["data"])
		else:
			return b""

	@functools.cached_property
	def stderr(self):
		if "stderr" in self._result_dict:
			return base64.b64decode(self._result_dict["stderr"]["data"])
		else:
			return b""

	@functools.cached_property
	def stdout_json(self):
		try:
			data = json.loads(self.stdout)
			self._have_stdout_json = True
		except json.decoder.JSONDecodeError:
			data = None
			self._have_stdout_json = False
		return data

	@property
	def have_json_output(self):
		if self._have_stdout_json is None:
			# Attempt to parse
			self.stdout_json
		return self._have_stdout_json

	@property
	def cmd(self):
		return self._result_dict["cmd"]

	@property
	def status(self):
		return getattr(ExecutionResult, self._result_dict["status"])

	def dump_stdout_stderr(self):
		print(self.stderr)
		print(self.stdout)

	def to_dict(self) -> dict:
		return self._result_dict

	def __str__(self):
		return f"SubprocessExecutionResult<{self.cmd[0]}: {self.status.name}>"

