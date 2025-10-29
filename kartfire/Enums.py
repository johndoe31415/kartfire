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

import enum

class TestrunStatus(enum.Enum):
	Skipped = "skipped"				# e.g., if a build step need not be executed
	Running = "running"				# Still running
	Finished = "finished"			# Run ran to completion
	Failed = "failed"				# Something failed to start the run (e.g., docker container start error)
	Aborted = "aborted"				# User aborted run (e.g., Ctrl-C)
	Terminated = "terminated"		# Run aborted (e.g., timeout or killed because of excessive resource use)

class TestresultStatus(enum.Enum):
	NoAnswer = "no_answer"				# No answer given
	Pass = "pass"						# Correct answer
	Fail = "fail"						# Wrong answer
	Indeterminate = "indeterminate"		# Reference solution not available, cannot judge if answer is correct or not
