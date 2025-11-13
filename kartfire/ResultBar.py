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
import dataclasses

class ResultBar():
	@dataclasses.dataclass
	class Element():
		element_type: str
		character: str
		alias: str | None = None
		prefix: str | None = None
		suffix: str | None = None
		force_nonzero_show: bool = False

	def __init__(self, length: int = 30, sort_by_most_common: bool = True):
		self._length = length
		self._sort_by_most_common = sort_by_most_common
		self._elements = collections.OrderedDict()

	@property
	def count_other(self):
		return None in self._elements

	def add(self, element: "Element"):
		if element.element_type in self._elements:
			raise ValueError(f"Duplicate element type: {element}")
		self._elements[element.element_type] = element
		return self

	def set_other(self, element: "Element | None"):
		element.element_type = None
		return self.add(element)

	def _select_relevant_items(self, distribution_dict: dict):
		relevant_items = { }
		other_count = 0
		for (key, count) in distribution_dict.items():
			if key in self._elements:
				if self._elements[key].alias is not None:
					key = self._elements[key].alias
				relevant_items[key] = relevant_items.get(key, 0) + count
			elif self.count_other:
				relevant_items[None] = relevant_items.get(None, 0) + count
		return relevant_items

	def _sort_relevant_items(self, relevant_items: dict) -> dict:
		if self._sort_by_most_common:
			order = [ name for (name, count) in sorted(relevant_items.items(), key = lambda item: -item[1]) ]
		else:
			order = [ name for name in self._elements if name in relevant_items ]
		result = collections.OrderedDict()
		for key in order:
			result[key] = relevant_items[key]
		return result

	def _scale_items(self, relevant_items: dict, scalar: float) -> dict:
		scaled_counts = collections.OrderedDict()
		for (key, count) in relevant_items.items():
			scaled_count = round(scalar * count)
			if self._elements[key].force_nonzero_show:
				scaled_count = max(1, scaled_count)
			scaled_counts[key] = scaled_count
		return scaled_counts

	def __call__(self, distribution_dict: dict):
		relevant_items = self._select_relevant_items(distribution_dict)
		relevant_items = self._sort_relevant_items(relevant_items)

		total_count = sum(relevant_items.values())
		offset = 0

		while True:
			scaled_counts = self._scale_items(relevant_items, (self._length - offset) / total_count)
			char_count = sum(scaled_counts.values())
			if char_count > self._length:
				offset += (char_count - self._length) / 2
			else:
				break
		assert(char_count == self._length)

		result_bar_items = [ ]
		for (key, count) in scaled_counts.items():
			element = self._elements[key]
			if element.prefix is not None:
				result_bar_items.append(element.prefix)
			result_bar_items.append(count * element.character)
			if element.suffix is not None:
				result_bar_items.append(element.suffix)
		return "".join(result_bar_items)

	def call__(self, run_result: "RunResult"):
		if not run_result.have_results:
			# No tests run?
			return "[" + (" " * self._length) + "]"

		result = { }
		total_chars_used = 0
		for (value, symbol, color) in self._display:
			match_count = run_result.result_count_dict.get(value, 0)
			if match_count > 0:
				char_count = max(1, round(match_count / run_result.total_testcase_count * self._length))
				total_chars_used += char_count
				result[value] = char_count

		while total_chars_used > self._length:
			maxc = max(result.values())
			for (value, count) in result.items():
				if count == maxc:
					result[value] -= 1
					total_chars_used -= 1

		result_string = [ "[" ]
		for (value, symbol, color) in self._display:
			if value in result:
				result_string.append(f"{color}{symbol * result[value]}{self._clear_color}")
		result_string += [ "]" ]
		return "".join(result_string)

if __name__ == "__main__":
	rb = ResultBar(30, sort_by_most_common = True)
	rb.add(ResultBar.Element(element_type = "pass", character = "+"))
	rb.add(ResultBar.Element(element_type = "weird_pass", character = None, alias = "pass"))
	rb.add(ResultBar.Element(element_type = "fail", character = "-", force_nonzero_show = True))
	rb.set_other(ResultBar.Element(element_type = None, character = "?"))

	results = { "pass": 49, "weird_pass": 1 }
	for i in range(150):
		results["fail"] = i
		print(rb(results))



