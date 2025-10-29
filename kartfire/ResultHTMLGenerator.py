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

import os
import tzlocal
import mako.lookup
from .RunResult import MultiRunResult

class ResultHTMLGenerator():
	def __init__(self, db: "Database"):
		self._db = db
		self._output_tz = tzlocal.get_localzone()
		template_dir = os.path.dirname(__file__) + "/templates"
		self._lookup = mako.lookup.TemplateLookup([ template_dir ], strict_undefined = True)

	def create(self, multirun_id: int, template_name: str):
		template = self._lookup.get_template(template_name)
		template_vars = {
			"r": MultiRunResult(db = self._db, multirun_id = multirun_id),
		}
		rendered = template.render(**template_vars)
		return rendered
