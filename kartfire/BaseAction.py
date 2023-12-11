#	kartfire - Test framework to consistently run submission files
#	Copyright (C) 2023-2023 Johannes Bauer
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

import logging

class BaseAction():
	def __init__(self, cmdname, args):
		self._cmdname = cmdname
		self._args = args
		self._setup_logging()

	def _setup_logging(self):
		if self._args.verbose == 0:
			loglevel = logging.WARNING
		elif self._args.verbose == 1:
			loglevel = logging.INFO
		else:
			loglevel = logging.DEBUG
		logging.basicConfig(format = "{name:>40s} [{levelname:.2s}]: {message}", style = "{", level = loglevel)

	def run(self):
		raise NotImplementedError(self.__class__)
