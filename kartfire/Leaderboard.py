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

import collections
from .ResultBar import ResultBar

class Leaderboard():
	def __init__(self, db: "Database", collection_name: str):
		self._db = db
		self._collection_name = collection_name
		self._collection = self._db.get_testcase_collection(collection_name)
		self._leaderboard = self._db.get_leaderboard(collection_name)
		for entry in self._leaderboard:
			filetypes = entry["source_metadata"]["meta"]["filetypes"]
			(entry["loc"], entry["language_breakdown"], entry["language_breakdown_text"]) = self._pgm_language_breakdown(filetypes)
			entry["reltime"] = entry["min_runtime_secs"] / self._collection.reference_runtime_secs

	@property
	def collection(self):
		return self._collection

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

	def _pgm_language_breakdown(self, filetypes: dict):
		known_filetypes = {
			".java":	"Java",
			".c":		"C",
			".h":		"C",
			".cpp":		"C++",
			".c++":		"C++",
			".hpp":		"C++",
			".h++":		"C++",
			".py":		"Python",
			".go":		"Go",
			".rs":		"Rust",
		}
		counter = collections.Counter()
		for (filetype, linecount) in filetypes.items():
			if filetype in known_filetypes:
				counter[known_filetypes[filetype]] += linecount
		total_lines = sum(counter.values())
		if total_lines == 0:
			return (total_lines, "-")

		breakdown = ", ".join(f"{linecount / total_lines * 100:.0f}% {language}" for (language, linecount) in counter.most_common(3))
		return (total_lines, counter, breakdown)

	def __iter__(self):
		return iter(self._leaderboard)

	def to_dict(self):
		def _entry_to_dict(entry):
			return {
				"run_id": entry["run_id"],
				"alias": entry["alias"],
				"source": entry["source"],
				"min_runtime_secs": entry["min_runtime_secs"],
				"loc_by_language": entry["language_breakdown"].most_common(3),
				"loc": entry["loc"],
			}

		return {
			"collection": self._collection.to_dict(),
			"entries": [ _entry_to_dict(entry) for entry in self._leaderboard ],
		}
