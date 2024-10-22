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
import re
import hashlib
import base64
import json
import asyncio
import subprocess
from .Exceptions import InternalError, SubprocessRunError
from .CmdlineEscape import CmdlineEscape

class JSONTools():
	@classmethod
	def canonicalize(cls, serializable_object):
		canonical_representation = json.dumps(serializable_object, separators = (",", ":"), sort_keys = True)
		return canonical_representation

	@classmethod
	def jsonhash(cls, serializable_object):
		canonical_representation = cls.canonicalize(serializable_object).encode("ascii")
		return hashlib.sha256(canonical_representation).hexdigest()

	@classmethod
	def encode_b64(cls, serializable_object):
		canonical_representation = cls.canonicalize(serializable_object)
		return base64.b64encode(canonical_representation.encode("ascii")).decode("ascii")

class GitTools():
	@classmethod
	def gitinfo(cls, dirname):
		if not os.path.isdir(f"{dirname}/.git"):
			return None
		result = {
			"empty": cls._is_repo_empty(dirname),
			"branch": cls._get_branch_name(dirname),
		}
		result["has_branch"] = cls._has_branch(dirname, result["branch"])

		if (not result["empty"]) and result["has_branch"]:
			result.update({
				"commit": cls._get_commit_id(dirname),
				"date": cls._get_commit_date(dirname),
			})
			result["shortcommit"] = result["commit"][:8]
		return result

	@classmethod
	def _is_repo_empty(cls, dirname):
		return subprocess.check_output([ "git", "-C", dirname, "rev-list", "--all", "-n", "1" ]).decode().rstrip("\r\n") == ""

	@classmethod
	def _has_commit_date(cls, dirname):
		return subprocess.check_output([ "git", "-C", dirname, "show", "--no-patch", "--format=%ci", "HEAD" ]).decode().rstrip("\r\n")

	@classmethod
	def _get_branch_name(cls, dirname):
		return subprocess.check_output([ "git", "-C", dirname, "branch", "--show-current" ]).decode().rstrip("\r\n")

	@classmethod
	def _get_commit_id(cls, dirname):
		return subprocess.check_output([ "git", "-C", dirname, "rev-parse", "HEAD" ]).decode().rstrip("\r\n")

	@classmethod
	def _get_commit_date(cls, dirname):
		return subprocess.check_output([ "git", "-C", dirname, "show", "--no-patch", "--format=%ci", "HEAD" ]).decode().rstrip("\r\n")

	@classmethod
	def _has_branch(cls, dirname: str, branch_name: str):
		return subprocess.run([ "git", "-C", dirname, "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}" ], stdout = subprocess.DEVNULL).returncode == 0

class SystemTools():
	_TOTAL_MEM_RE = re.compile(r"MemTotal:\s*(?P<mem_kib>\d+)\s*kB")

	@classmethod
	def get_host_memory_mib(cls):
		with open("/proc/meminfo") as f:
			rematch = cls._TOTAL_MEM_RE.search(f.read())
		if rematch is None:
			raise InternalError("Unable to determine total amount of available RAM.")
		return int(rematch.groupdict()["mem_kib"]) // 1024

class ExecTools():
	@classmethod
	async def async_check_output(cls, cmd: list):
		(stdout, stderr) = await cls.async_check_communicate(cmd)
		return stdout

	@classmethod
	async def async_check_communicate(cls, cmd: list):
#		print(cmd)
		proc = await asyncio.create_subprocess_exec(*cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
		(stdout, stderr) = await proc.communicate()
		if proc.returncode != 0:
			raise SubprocessRunError(f"Command failed to execute, returncode {proc.returncode}: {CmdlineEscape().cmdline(cmd)}")
		return (stdout, stderr)

	@classmethod
	async def async_check_call(cls, cmd: list, stdout = None, stderr = None):
		result = await cls.async_call(cmd = cmd, stdout = stdout, stderr = stderr)
		if result != 0:
			raise SubprocessRunError(f"Command failed to execute, returncode {result}: {CmdlineEscape().cmdline(cmd)}")

	@classmethod
	async def async_call(cls, cmd: list, stdout = None, stderr = None):
		proc = await asyncio.create_subprocess_exec(*cmd, stdout = stdout, stderr = stderr)
		result = await proc.wait()
		return result
