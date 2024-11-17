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

import enum

class TestcaseStatus(enum.Enum):
	Passed = "passed"													# Testcase returned correct result
	FailedWrongAnswer = "failed_wrong_answer"							# Testcase returned incorrect result
	NoAnswerProvided = "no_answer_provided"								# Testcase result not contained in result dict
	UnparsableAnswerProvided = "unparsable_answer_provided"				# Testcase returned data that is not parsable as JSON
	BuildTimedOut = "build_timed_out"									# Build process timed out
	BuildFailure = "build_failure"										# Build process was unsuccessful
	BatchFailedInvalidAnswerProvided = "invalid_answer_provided"		# Testcase returned JSON data that has invalid format
	BatchFailedNotExecutable = "batch_failed_not_executable"			# DUT was not executable, exec() failed
	BatchFailedUnparsableAnswerProvided = "batch_failed_unparsable"
	BatchFailedReturnCode = "batch_failed_returncode"
	BatchFailedTimeout = "batch_failed_timeout"
	BatchFailedExecExecption = "batch_failed_exec_exception"
	BatchFailedOutOfMemory = "batch_failed_oom"
	DockerRunFailed = "all_failed_docker"


class TestbatchStatus(enum.Enum):
	ErrorTestrunFailed = "error_run_failed"
	ErrorUnparsable = "error_unparsable"
	Completed = "completed"

class TestrunStatus(enum.Enum):
	Skipped = "skipped"
	ErrorUnparsable = "error_unparsable"
	ErrorStatusCode = "error_nonzero_status_code"
	ContainerTimeout = "container_timeout"
	Completed = "completed"

class ExecutionResult(enum.Enum):
	Success = "success"
	FailedReturnCode = "failed_return_code"
	FailedTimeout = "failed_timeout"
	FailedExecException = "failed_exec_exception"
	FailedNotExecutable = "failed_exec_not_executable"
	FailedOutOfMemory = "failed_oom"
