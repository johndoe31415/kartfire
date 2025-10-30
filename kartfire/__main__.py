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
from .ActionImport import ActionImport
from .ActionList import ActionList
from .ActionCollection import ActionCollection
from .ActionRun import ActionRun
from .ActionResults import ActionResults
from .ActionReference import ActionReference
from .ActionLeaderboard import ActionLeaderboard
from .ActionScram import ActionScram
from .ActionDockerPrune import ActionDockerPrune

def main():
	mc = MultiCommand(description = "Kartfire container testing framework CLI tool.", run_method = True)

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
		parser.add_argument("collection_name", help = "Test collection name(s) to execute, possibly separated by commas.")
		parser.add_argument("submission_dir", nargs = "+", help = "Directory/directories that should be run as a testcase inside containers.")
	mc.register("run", "Run solution(s) against a battery of testcases", genparser, action = ActionRun)

	def genparser(parser):
		parser.add_argument("--summary-by-run", action = "store_true", help = "Show individual runs, not consolidated multiruns")
		parser.add_argument("-H", "--html-template", metavar = "name", help = "Render a HTML output from the testruns")
		parser.add_argument("-D", "--database-filename", metavar = "file", default = "kartfire.sqlite3", help = "Database filename to use. Defaults to %(default)s.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
		parser.add_argument("run_multirun_id", type = ActionResults.id_type, nargs = "*", help = "Run or multirun ID(s) to show details of. Multirun IDs start with 'm'.")
	mc.register("results", "Print results of run testcases", genparser, action = ActionResults)

	def genparser(parser):
		parser.add_argument("-D", "--database-filename", metavar = "file", default = "kartfire.sqlite3", help = "Database filename to use. Defaults to %(default)s.")
		parser.add_argument("-a", "--allow-failed-status", action = "store_true", help = "Allow failed test run status and failed testcases.")
		parser.add_argument("-f", "--pick-failed-answers", action = "store_true", help = "Pick not only 'indeterminate' answers, but also those marked as wrong.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
		parser.add_argument("submission_name", help = "Name of the submission that was run and should be used as a reference.")
	mc.register("reference", "Mark a solution's results as the reference answers", genparser, action = ActionReference)

	def genparser(parser):
		parser.add_argument("-D", "--database-filename", metavar = "file", default = "kartfire.sqlite3", help = "Database filename to use. Defaults to %(default)s.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
		parser.add_argument("collection_name", help = "Test collection name(s) to judge, possibly separated by commas.")
	mc.register("leaderboard", "Get a leaderboard that comares the runtimes of runs that achieved all passes", genparser, action = ActionLeaderboard)

	def genparser(parser):
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
	mc.register("scram", "Perform a Docker SCRAM, effectively terminating every Docker-related things that were started by kartfire", genparser, action = ActionScram)

	def genparser(parser):
		parser.add_argument("-f", "--force", action = "store_true", help = "Remove also items that may appear to be used (e.g., images that Docker thinks are not dangling)")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
	mc.register("docker-prune", "Prune Docker remains (networks and dangling containers)", genparser, action = ActionDockerPrune)

	returncode = mc.run(sys.argv[1:])
	return (returncode or 0)


if __name__ == "__main__":
	sys.exit(main())
