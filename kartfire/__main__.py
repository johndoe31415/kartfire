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

import sys
from .MultiCommand import MultiCommand
#from .ActionRun import ActionRun
#from .ActionReference import ActionReference
#from .ActionRender import ActionRender
#from .ActionEmail import ActionEmail
#from .ActionMerge import ActionMerge
#from .ActionPrint import ActionPrint
#from .ActionLeaderboard import ActionLeaderboard
from .ActionImport import ActionImport
from .ActionList import ActionList
from .ActionCollection import ActionCollection
from .ActionRun import ActionRun

def main():
	mc = MultiCommand(description = "Kartfire container testing framework CLI tool.", run_method = True)

#	def genparser(parser):
#		parser.add_argument("-s", "--state-file", metavar = "filename", help = "Keep a state file and only run those testcases where a change occurred.")
#		parser.add_argument("-i", "--interactive", action = "store_true", help = "Start an interactive session to be able to debug inside the Docker container.")
#		parser.add_argument("-c", "--test-fixture-config", metavar = "filename", help = "Specify a specific test fixture configuration to use. If omitted, tries to look in the local directory for a file named 'kartfire_test_fixture.json' before falling back to default values.")
#		parser.add_argument("-f", "--testcase-file", metavar = "filename", action = "append", required = True, help = "Testcase definition JSON file. Can be given multiple times to join testcases. Mandatory argument.")
#		parser.add_argument("-o", "--output-file", metavar = "filename", help = "Write the JSON results to this file. If not given, an automatic name according to the testrun is chosen.")
#		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
#		parser.add_argument("submission_dir", nargs = "+", help = "Directory/directories that should be run as a testcase inside containers.")
#	mc.register("run", "Run a testcase battery", genparser, action = ActionRun)

#	def genparser(parser):
#		parser.add_argument("-C", "--commit", action = "store_true", help = "Write back results to the test case file.")
#		parser.add_argument("-c", "--test-fixture-config", metavar = "filename", help = "Specify a specific test fixture configuration to use. If omitted, tries to look in the local directory for a file named 'kartfire_test_fixture.json' before falling back to default values.")
#		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
#		parser.add_argument("reference_submission_dir", help = "Directory that contains the reference solution.")
#		parser.add_argument("testcase_filename", nargs = "+", help = "Testcase definition JSON file(s) that should be filled with the reference answers.")
#	mc.register("reference", "Collect reference answers from a known-good solution", genparser, action = ActionReference)

#	def genparser(parser):
#		parser.add_argument("-f", "--force", action = "store_true", help = "Overwrite output file if it already exists.")
#		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
#		parser.add_argument("template_filename", help = "Template input file that should be rendered.")
#		parser.add_argument("testcase_filename", help = "Testcase definition JSON file that is produced from the template.")
#	mc.register("render", "Render a testcase file from a template", genparser, action = ActionRender)

#	def genparser(parser):
#		parser.add_argument("-f", "--force", action = "store_true", help = "Overwrite output file if it already exists.")
#		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
#		parser.add_argument("testrun_filename", help = "JSON data that was output from the test run.")
#		parser.add_argument("makomailer_filename", help = "Makomailer output that should be created.")
#	mc.register("email", "Create a Makomailer template file from a output run", genparser, action = ActionEmail)

#	def genparser(parser):
#		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
#		parser.add_argument("source_filename", help = "JSON data that was output from a test run and that will be read.")
#		parser.add_argument("destination_filename", help = "JSON data that was output from a test run and that will be read and written.")
#	mc.register("merge", "Merge run results into one unified file", genparser, action = ActionMerge)

#	def genparser(parser):
#		parser.add_argument("-s", "--search", metavar = "search_term", action = "append", default = [ ], help = "Search term to search for repository owner (if available) and repository basename.")
#		parser.add_argument("-n", "--max-failed-testcase-count", metavar = "count", type = int, default = 1, help = "Show full testcase data (input, output, expected output) for this number of failed testcases.")
#		parser.add_argument("-d", "--details", action = "count", default = 0, help = "Increases detail level of printed output. Can be specified multiple times to increase.")
#		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
#		parser.add_argument("testrun_filename", help = "JSON data that was output from the test run.")
#	mc.register("print", "Print run results on the command line", genparser, action = ActionPrint)

#	def genparser(parser):
#		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
#		parser.add_argument("testrun_filename", help = "JSON data that was output from the test run.")
#	mc.register("leaderboard", "Print a time leaderboard", genparser, action = ActionLeaderboard)

	def genparser(parser):
		parser.add_argument("-D", "--database-filename", metavar = "file", default = "kartfire.sqlite3", help = "Database filename to use. Defaults to %(default)s.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
		parser.add_argument("testcase_filename", nargs = "+", help = "JSON data that should be read into the database.")
	mc.register("import", "Import testcase JSON file(s) into the database", genparser, action = ActionImport)

	def genparser(parser):
		parser.add_argument("-D", "--database-filename", metavar = "file", default = "kartfire.sqlite3", help = "Database filename to use. Defaults to %(default)s.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
		parser.add_argument("-c", "--collection-filter", metavar = "name", default = [ ], action = "append", help = "When present, list only those testcases present in all of the mentioned collection(s). Can be specified multiple times.")
	mc.register("list", "List testcases from database", genparser, action = ActionList)

	def genparser(parser):
		parser.add_argument("-D", "--database-filename", metavar = "file", default = "kartfire.sqlite3", help = "Database filename to use. Defaults to %(default)s.")
		parser.add_argument("-r", "--remove", action = "store_true", help = "By default, when a selector is specified, the entries are added to the named collection. When this is specified, the selected entries are removed instead.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
		parser.add_argument("collection_name", help = "Test collection name to manage.")
		parser.add_argument("testcase_selector", nargs = "?", help = "Testcase selector. Adds or removes the selected testcases to the named collection.")
	mc.register("collection", "Manage collections of testcases", genparser, action = ActionCollection)

	def genparser(parser):
		parser.add_argument("-i", "--interactive", action = "store_true", help = "Interactively debug the session by dropping into a shell.")
		parser.add_argument("-t", "--time-scalar", metavar = "float", type = float, default = 1.0, help = "Multiply the allowed time by this scalar factor. When zero is specified, runtime is infinite.")
		parser.add_argument("-C", "--test-fixture-config", metavar = "filename", help = "Specify a specific test fixture configuration to use. If omitted, tries to look in the local directory for a file named 'kartfire_test_fixture.json' before falling back to default values.")
		parser.add_argument("-D", "--database-filename", metavar = "file", default = "kartfire.sqlite3", help = "Database filename to use. Defaults to %(default)s.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
		parser.add_argument("collection_name", help = "Test collection name to execute.")
		parser.add_argument("submission_dir", nargs = "+", help = "Directory/directories that should be run as a testcase inside containers.")
	mc.register("run", "Run solution(s) against a battery of testcases", genparser, action = ActionRun)

	returncode = mc.run(sys.argv[1:])
	return (returncode or 0)


if __name__ == "__main__":
	sys.exit(main())
