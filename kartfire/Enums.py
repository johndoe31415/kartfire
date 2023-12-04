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

import enum

class TestcaseStatus(enum.Enum):
	Passed = "passed"
	FailedWrongAnswer = "failed_wrong_answer"
	FailedUnparsableAnswer = "failed_unparsable"
	FailedErrorStatusCode = "failed_error_status_code"
	FailedTimeout = "failed_timeout"
	FailedRunError = "failed_run_error"

class TestrunStatus(enum.Enum):
	Skipped = "skipped"
	ErrorUnparsable = "error_unparsable"
	ErrorStatusCode = "error_nonzero_status_code"
	Timeout = "container_timeout"
	Completed = "completed"
