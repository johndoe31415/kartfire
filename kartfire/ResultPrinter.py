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

import datetime
import tzlocal
import pytz
import json
from .Enums import TestrunStatus
from .TimeDelta import TimeDelta

class ResultColorizer():
	def __init__(self, ansi: bool = True):
		self._ansi = ansi

	@property
	def clr(self):
		return "\x1b[0m" if self._ansi else ""

	@property
	def red(self):
		return "\x1b[31m" if self._ansi else ""

	@property
	def green(self):
		return "\x1b[32m" if self._ansi else ""

	@property
	def yellow(self):
		return "\x1b[33m" if self._ansi else ""

	def ratio(self, ratio: float):
		if ratio < 0:
			ratio = 0
		elif ratio > 1:
			ratio = 1
		if ratio < 0.66:
			return self.red
		elif ratio < 1:
			return self.yellow
		else:
			return self.green

class ResultPrinter():
	def __init__(self, db: "Database"):
		self._db = db
		self._output_tz = tzlocal.get_localzone()

	def _parse_utc_ts_str(self, utc_ts_str: str):
		return datetime.datetime.strptime(utc_ts_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo = datetime.UTC)

	def _fmtts(self, utc_ts_str: str, format_str: str = "full"):
		ts = self._parse_utc_ts_str(utc_ts_str)
		local_ts = ts.astimezone(self._output_tz)
		match format_str:
			case "full":
				return local_ts.strftime("%Y-%m-%d %H:%M")

			case "time":
				return local_ts.strftime("%H:%M")

			case _:
				raise ValueError(format_str)

	def _timedelta(self, utc_ts_str1: str, utc_ts_str2: str):
		ts1 = self._parse_utc_ts_str(utc_ts_str1)
		ts2 = self._parse_utc_ts_str(utc_ts_str2)
		return TimeDelta(ts1, ts2)

	def _print_overview(self, row: "Row"):
		td = self._timedelta(row["run_start_ts"], row["run_end_ts"])
		error_details = json.loads(row["error_details"])
		columns = [
			f"{row['runid']:5d}",
			f"{row['source']:15s}",
			f"{TestrunStatus(row['status']).name:14s}",
			f"  {self._fmtts(row['run_start_ts'])}-{self._fmtts(row['run_end_ts'], 'time')}",
			f"  {td}  ",
			f"  {td:d}  ",
		]
		if error_details is not None:
			columns.append(f"{error_details['text']}")
		print(" ".join(columns))

	def print_overview(self, runid: int):
		row = self._db.get_run_overview(runid)
		self._print_overview(row)
