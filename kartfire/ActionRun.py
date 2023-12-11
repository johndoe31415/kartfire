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
from .TestFixtureConfig import TestFixtureConfig
from .TestcaseRunner import TestcaseRunner
from .TestcaseCollection import TestcaseCollection
from .Submission import Submission
from .BaseAction import BaseAction

class ActionRun(BaseAction):
	def run(self):
		if self._args.test_fixture_config is not None:
			test_fixture_config = TestFixtureConfig.load_from_file(self._args.test_fixture_config)
		else:
			test_fixture_config = TestFixtureConfig()

		testcase_collections = [ TestcaseCollection.load_from_file(tc_filename, test_fixture_config) for tc_filename in self._args.testcase_file ]
		submissions = [ Submission(submission) for submission in self._args.submission ]
		tcr = TestcaseRunner(testcase_collections = testcase_collections, test_fixture_config = test_fixture_config)
		tcr.run(submissions)
