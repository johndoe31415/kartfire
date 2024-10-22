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

import os
import json
from .BaseAction import BaseAction

class ActionEmail(BaseAction):
	def run(self):
		if (not self._args.force) and os.path.exists(self._args.makomailer_filename):
			print(f"Refusing to overwrite: {self._args.makomailer_json_filename}", file = sys.stderr)
			return 1

		with open(self._args.testrun_filename) as f:
			test_results = json.load(f)

		makomailer_output = {
			"global": test_results["meta"],
			"individual": test_results["content"],
		}

		with open(self._args.makomailer_filename, "w") as f:
			json.dump(makomailer_output, f)


