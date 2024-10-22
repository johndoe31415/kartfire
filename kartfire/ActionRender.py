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
import os
import base64
import json
import logging
import datetime
import collections
import copy
import random
import itertools
from .TestFixtureConfig import TestFixtureConfig
from .TestcaseRunner import TestcaseRunner
from .TestcaseCollection import TestcaseCollection
from .Submission import Submission
from .BaseAction import BaseAction

class SubstitutionElement():
	def __init__(self, content: dict, context: dict):
		self._content = content
		self._context = context
		self._enacted_value = None

	@property
	def subs_type(self):
		return self._content["_sub"]

	@property
	def enacted_value(self):
		return self._enacted_value

	@enacted_value.setter
	def enacted_value(self, value):
		self._enacted_value = value

	def __iter__(self):
		match self.subs_type:
			case "enumeration":
				name = self._content["name"]
				enumeration = self._context.get("enumerations", { }).get(name)
				if enumeration is None:
					raise ValueError(f"No such enumeration: {name}")
				yield from enumeration

			case "rand-base64":
				count = self._content.get("count", 1)

				for count in range(count):
					if "length" in self._content:
						length = self._content["length"]
					else:
						length = random.randint(self._content["minlength"], self._content["maxlength"])
					if "lengthmul" in self._content:
						length *= self._content["lengthmul"]

					rand_data = os.urandom(length)
					yield base64.b64encode(rand_data).decode("ascii")

			case "int-set":
				minlen = self._content.get("minlen", 0)
				maxlen = self._content.get("maxlen", 32)
				minval = self._content.get("minval", 0)
				maxval = self._content.get("maxval", 255)
				shuffle = self._content.get("shuffle", True)
				count = self._content.get("count", 1)
				for _ in range(count):
					result = set()
					length = random.randint(minlen, maxlen)
					while len(result) < length:
						result.add(random.randint(minval, maxval))

					result = list(result)
					if shuffle:
						random.shuffle(result)
					else:
						result.sort()
					yield result

			case _:
				raise ValueError(f"Unknown substitution type: {self.subs_type}")

class ActionRender(BaseAction):
	def _replace_substitution_elements(self, element):
		if isinstance(element, (int, str, float, type(None))):
			return element
		elif isinstance(element, list):
			return [ self._replace_substitution_elements(item) for item in element ]
		elif isinstance(element, dict):
			if "_sub" in element:
				return SubstitutionElement(element, context = self._context)
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
		if (not self._args.force) and os.path.exists(self._args.testcase_filename):
			print(f"Refusing to overwrite: {self._args.testcase_filename}", file = sys.stderr)
			return 1

		with open(self._args.template_filename) as f:
			self._template = json.load(f, object_pairs_hook = collections.OrderedDict)
		if self._template["meta"]["type"] != "template":
			print(f"Not a template: {self._args.testcase_filename}", file = sys.stderr)
			return 1

		self._context = self._template.get("template", { })

		rendered_testcases = [ ]
		for testcase_definition in self._template["content"]:
			for rendered_instance in self._render(testcase_definition):
				rendered_testcases.append(rendered_instance)

		print(f"Rendered {len(self._template['content'])} templates to {len(rendered_testcases)} testcases.")
		self._template["meta"]["type"] = "testcases"
		self._template["content"] = rendered_testcases
		if "template" in self._template:
			del self._template["template"]

		with open(self._args.testcase_filename, "w") as f:
			json.dump(self._template, f, indent = "\t")
			print(file = f)
