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

from .MultiCommand import LoggingAction
from .Database import Database
from .TestFixtureConfig import TestFixtureConfig

class CmdlineAction(LoggingAction):
	def __init__(self, cmd: str, args):
		super().__init__(cmd, args)
		if hasattr(self._args, "database_filename"):
			self._db = Database(self._args.database_filename)
		if hasattr(self._args, "test_fixture_config"):
			self._test_fixture_config = TestFixtureConfig.load_from_file(self._args.test_fixture_config)
