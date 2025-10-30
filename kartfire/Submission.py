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
import json
import functools
from .Exceptions import InvalidSubmissionException
from .Tools import ExecTools, GitTools, MiscTools

class Submission():
	def __init__(self, submission_directory: str, test_fixture_config: "TestFixtureConfig"):
		self._submission_dir = os.path.realpath(submission_directory)
		self._test_fixture_config = test_fixture_config
		if not os.path.isdir(self._submission_dir):
			raise InvalidSubmissionException(f"{self._submission_dir} is not a directory")

	@property
	def shortname(self):
		return os.path.basename(self._submission_dir)

	@property
	def requires_build_step(self):
		build_script_filename = f"{self._submission_dir}/{self._test_fixture_config.setup_name}"
		return os.path.exists(build_script_filename)

	@functools.cached_property
	def meta_info(self):
		meta = { }
		git_info = GitTools.gitinfo(self._submission_dir)
		if git_info is not None:
			meta["git"] = git_info

		json_filename = f"{self._submission_dir}.json"
		if os.path.isfile(json_filename):
			with open(json_filename) as f:
				meta["json"] = json.load(f)
		meta["filetypes"] = MiscTools.determine_lines_by_file_extension(self._submission_dir)
		return meta

	async def create_submission_tarfile(self, tarfile_name: str):
		await ExecTools.async_check_call([ "tar", "-C", self._submission_dir, "-c", "-f", tarfile_name, "." ])

	def to_dict(self):
		return {
			"dirname": self._submission_dir,
			"meta": self.meta_info,
		}

	def __str__(self):
		short_dir = os.path.basename(self._submission_dir)
		meta = self.meta_info
		if ("json" in meta) and ("text" in meta["json"]):
			return f"{short_dir}: {meta['json']['text']}"
		elif "git" in meta:
			if meta["git"]["empty"]:
				return f"{short_dir}: empty Git repository"
			elif not meta["git"]["has_branch"]:
				return f"{short_dir}: no branch {meta['git']['branch']}"
			else:
				return f"{short_dir}: {meta['git']['branch']} / {meta['git']['commit'][:8]}"
		else:
			return short_dir
