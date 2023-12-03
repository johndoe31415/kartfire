#	kartfire - Test framework to consistently run submission files
#	Copyright (C) 2023-2023 Johannes Bauer
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

class GitTools():
	@classmethod
	def gitinfo(cls, dirname):
		if not os.path.isdir(f"{dirname}/.git"):
			return None
		return {
			"branch": cls._get_branch_name(dirname),
			"commit": cls._get_commit_id(dirname),
			"date": cls._get_commit_date(dirname),
		}
		result["shortcommit"] = result["commit"][:8]
		return result

	@classmethod
	def _git_branch_name(cls, dirname):
			return subprocess.check_output([ "git", "-C", dirname, "branch", "--show-current" ]).decode().rstrip("\r\n")

	@classmethod
	def _git_commit_id(cls, dirname):
			return subprocess.check_output([ "git", "-C", dirname, "rev-parse", "HEAD" ]).decode().rstrip("\r\n")

	@classmethod
	def _git_commit_date(cls, dirname):
			return subprocess.check_output([ "git", "-C", dirname, "show", "--no-patch", "--format=%ci", "HEAD" ]).decode().rstrip("\r\n")
