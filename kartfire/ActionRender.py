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
import base64
import json
import logging
import datetime
import collections
import copy
import itertools
from .TestFixtureConfig import TestFixtureConfig
from .TestcaseRunner import TestcaseRunner
from .TestcaseCollection import TestcaseCollection
from .Submission import Submission
from .BaseAction import BaseAction

class SubstitutionElement():
	def __init__(self, content: dict):
		self._content = content
		self._enacted_value = None

	@property
	def subs_type(self):
		return self._content["_subs"]

	@property
	def enacted_value(self):
		return self._enacted_value

	@enacted_value.setter
	def enacted_value(self, value):
		self._enacted_value = value

	def __iter__(self):
		if self.subs_type == "int3":
			yield from [ 1, 2, 3 ]
		else:
			yield from [ "A", "B", "C" ]

class ActionRender(BaseAction):
	def _replace_substitution_elements(self, element):
		if isinstance(element, (int, str, float, type(None))):
			return element
		elif isinstance(element, list):
			return [ self._replace_substitution_elements(item) for item in element ]
		elif isinstance(element, dict):
			if "_subs" in element:
				return SubstitutionElement(element)
			else:
				return collections.OrderedDict((key, self._replace_substitution_elements(value)) for (key, value) in element.items())
		else:
			raise ValueError(element)

	def _find_substitution_iterators(self, element, iterators = None):
		if iterators is None:
			iterators = [ ]
		if isinstance(element, SubstitutionElement):
			iterators.append(element)
		elif isinstance(element, list):
			for item in element:
				self._find_substitution_iterators(item, iterators)
		elif isinstance(element, dict):
			for item in element.values():
				self._find_substitution_iterators(item, iterators)
		return iterators

	def _enact_substitutions(self, element):
		if isinstance(element, SubstitutionElement):
			return element.enacted_value
		elif isinstance(element, list):
			return [ self._enact_substitutions(item) for item in element ]
		elif isinstance(element, dict):
			return collections.OrderedDict((key, self._enact_substitutions(value)) for (key, value) in element.items())
		else:
			return element

	def _render(self, element):
		element = self._replace_substitution_elements(element)
		iterators = self._find_substitution_iterators(element)

		for iterator_values in itertools.product(*iterators):
			for (iterator, iterator_value) in zip(iterators, iterator_values):
				iterator.enacted_value = iterator_value

			instance = self._enact_substitutions(element)
			yield copy.deepcopy(instance)

	def run(self):
		with open(self._args.template_filename) as f:
			self._template = json.load(f, object_pairs_hook = collections.OrderedDict)

		x = {
			"foo": "bar",
			"zahl": 1234,
			"array": [ 1, 2, 3, 4 ],
			"blah": [ "vor", { "_subs": "alpha3" }, "nach" ],
			"blah2": { "moo": [ 1, 2, { "_subs": "int3" } ], "blah": { "_subs": "int3" } },
		}
		for variant in self._render(x):
			print(variant)

#		rendered_testcases = [ ]
#		for testcase_definition in self._template["content"]:
#			rendered_testcases += list(self._render_recursive(testcase_definition))

#		print(f"Rendered {len(self._template['content'])} templates to {len(rendered_testcases)} testcases.")

