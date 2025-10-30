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

class TimeDelta():
	def __init__(self, duration_secs: float | None = None):
		self._duration_secs = duration_secs

	@property
	def undefined(self):
		return self._duration_secs is None

	@property
	def duration_secs(self):
		return self._duration_secs

	def _duration_text(self, secs: float):
		if secs < 1:
			return f"{secs * 1000:.0f} ms"
		else:
			secs = round(secs)
			if secs < 60:
				return f"{secs} sec"
			elif secs < 60 * 60:
				return f"{secs // 60}:{secs % 60:02d} m:s"
			elif secs < 24 * 60 * 60:
				return f"{secs // 3600}:{secs % 3600 // 60:02d}:{secs % 3600 % 60:02d} h:m:s"
			else:
				(days, secs) = divmod(secs, 86400)
				return f"{days}d {secs // 3600}:{secs % 3600 // 60:02d}:{secs % 3600 % 60:02d} h:m:s"

	def _event_text(self, secs: float):
		if secs < 1:
			return f"{secs * 1000:.0f} ms"
		elif secs < 60:
			secs = round(secs)
			return f"{secs} second{'s' if secs != 1 else ''}"
		elif secs < 60 * 60:
			mins = round(secs / 60)
			return f"{mins} minute{'s' if mins != 1 else ''}"
		elif secs < 24 * 60 * 60:
			hrs = round(secs / 3600)
			return f"{hrs} hour{'s' if hrs != 1 else ''}"
		elif secs < 30 * 24 * 60 * 60:
			days = int(secs) // 86400
			hrs = round((int(secs) % 86400) / 3600)
			return f"{days} day{'s' if days != 1 else ''} and {hrs} hour{'s' if hrs != 1 else ''}"
		else:
			days = round(secs / 86400)
			return f"{days} day{'s' if days != 1 else ''}"

	def __format__(self, fmtstr: str):
		if self.duration_secs is None:
			return "N/A"

		if fmtstr == "d":
			return self._duration_text(self.duration_secs)
		else:
			if self.duration_secs < 0:
				return f"in {self._event_text(-self.duration_secs)}"
			else:
				return f"{self._event_text(self.duration_secs)} ago"

	def __str__(self):
		return format(self)
