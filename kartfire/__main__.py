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

import sys
from .MultiCommand import MultiCommand
from .ActionRun import ActionRun

def main():
	mc = MultiCommand(description = "Kartfire container testing framework CLI tool.", run_method = True)

	def genparser(parser):
		parser.add_argument("-i", "--interactive", action = "store_true", help = "Start an interactive session to be able to debug inside the Docker container.")
		parser.add_argument("-c", "--test-fixture-config", metavar = "filename", help = "Specify a specific test fixture configuration to use. If omitted, tries to look in the local directory for a file named 'kartfire_test_fixture.json' before falling back to default values.")
		parser.add_argument("-f", "--testcase-file", metavar = "filename", action = "append", required = True, help = "Testcase definition JSON file. Can be given multiple times to join testcases. Mandatory argument.")
		parser.add_argument("-o", "--output-file", metavar = "filename", help = "Write the JSON results to this file. If not given, an automatic name according to the testrun is chosen.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
		parser.add_argument("submission", nargs = "+", help = "Directory/directories that should be run as a testcase inside containers.")
	mc.register("run", "Run a testcase battery", genparser, action = ActionRun)

	returncode = mc.run(sys.argv[1:])
	return (returncode or 0)


if __name__ == "__main__":
	sys.exit(main())
