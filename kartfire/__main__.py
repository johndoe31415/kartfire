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

import sys
from .FriendlyArgumentParser import FriendlyArgumentParser
from .TestFixtureConfig import TestFixtureConfig
from .TestcaseRunner import TestcaseRunner
from .TestcaseCollection import TestcaseCollection

def main():
	parser = FriendlyArgumentParser(description = "Kartfire test running application.")
	parser.add_argument("-c", "--test-fixture-config", metavar = "filename", help = "Specify a specific test fixture configuration to use.")
	parser.add_argument("-f", "--testcase-file", metavar = "filename", action = "append", required = True, help = "Testcase definition JSON file. Can be given multiple times to join testcases. Mandatory argument.")
	parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
	parser.add_argument("testcase", nargs = "+", help = "Directory/directories that should be run as a testcase inside containers.")
	args = parser.parse_args(sys.argv[1:])

	testcase_collections = [ TestcaseCollection.load_from_file(tc_filename) for tc_filename in args.testcase_file ]
	test_fixture_config = TestFixtureConfig.load_from_file(args.test_fixture_config)
	tcr = TestcaseRunner(testcase_collections = testcase_collections, test_fixture_config = test_fixture_config)
	tcr.run()

if __name__ == "__main__":
	main()
