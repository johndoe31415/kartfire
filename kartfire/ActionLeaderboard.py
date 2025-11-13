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

from .CmdlineAction import CmdlineAction
from .TableFormatter import Table, CellFormatter
from .ResultBar import ResultBar

class ActionLeaderboard(CmdlineAction):
	def _pgm_language_bar(self):
		rb = ResultBar(1)
		rb.add(ResultBar.Element(element_type = ".java", character = "☕"))
		rb.add(ResultBar.Element(element_type = ".c", character = "🅒"))
		rb.add(ResultBar.Element(element_type = ".h", character = None, alias = ".c"))
		rb.add(ResultBar.Element(element_type = ".cpp", character = "➕"))
		rb.add(ResultBar.Element(element_type = ".hpp", character = None, alias = ".cpp"))
		rb.add(ResultBar.Element(element_type = ".c++", character = None, alias = ".cpp"))
		rb.add(ResultBar.Element(element_type = ".h++", character = None, alias = ".cpp"))
		rb.add(ResultBar.Element(element_type = ".py", character = "🐍"))
		rb.add(ResultBar.Element(element_type = ".rs", character = "🦀"))
		rb.add(ResultBar.Element(element_type = ".go", character = "🐿️"))
		return rb

	def run(self):
		collection = self._db.get_testcase_collection(self._args.collection_name)

		leaderboard = self._db.get_leaderboard(self._args.collection_name)
		print(f"Best runs for collection {self._args.collection_name} with all pass results, reftime {collection.reference_runtime_secs:.2f} sec")

		table = Table()
		table.format_columns({
			"time":		CellFormatter(align = CellFormatter.Alignment.Right, content_to_str_fnc = lambda content: f"{content:.1f}"),
			"reltime":	CellFormatter(align = CellFormatter.Alignment.Right, content_to_str_fnc = lambda content: f"{content:6.1f}%"),
			"relfactor":	CellFormatter(align = CellFormatter.Alignment.Right, content_to_str_fnc = lambda content: f"{content:.1f}x"),
		})
		table.add_row({
			"source":		"Source",
			"run_id":		"Run ID",
			"time":			"Time/secs",
			"reltime":		"Relative time",
			"relfactor":	"Factor",
			"language":		"Lang",
		}, cell_formatters = {
			"time": table["time"].override(content_to_str_fnc = str),
			"reltime": table["reltime"].override(content_to_str_fnc = str),
			"relfactor": table["relfactor"].override(content_to_str_fnc = str),
		})
		table.add_separator_row()


		pgm_language_bar = self._pgm_language_bar()
		for entry in leaderboard:
			kartfire_meta = entry["source_metadata"]["meta"].get("json", { }).get("kartfire", { })
			if self._args.show_real_name:
				source = kartfire_meta.get("name") or entry["alias"] or entry["source"]
			else:
				source = entry["alias"] or entry["source"]
			language = pgm_language_bar(entry["source_metadata"]["meta"]["filetypes"])
			table.add_row({
				"source":		source,
				"run_id":		entry["run_id"],
				"time":			entry["min_runtime_secs"],
				"reltime":		entry['min_runtime_secs'] / collection.reference_runtime_secs * 100,
				"relfactor":	collection.reference_runtime_secs / entry['min_runtime_secs'],
				"language":		language,
			})

		table.print("source", "run_id", "time", "reltime", "relfactor", "language")
