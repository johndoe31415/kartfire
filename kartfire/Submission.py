#	kartfire - The X.509 Swiss Army Knife white-hat certificate toolkit
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

import os
from .Exceptions import InvalidSubmissionException

class Submission():
	def __init__(self, submission_directory):
		self._submission_dir = os.path.realpath(submission_directory)
		if not os.path.isdir(self._submission_dir):
			raise InvalidSubmissionException(f"{self._submission_dir} is not a directory")

	def _create_submission_tarfile(self, tarfile_name):
		pass
