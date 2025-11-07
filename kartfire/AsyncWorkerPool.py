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

import asyncio

class AsyncWorkerPool():
	def __init__(self, pool_max_size: int, exception_callback: "callable | None" = None):
		self._pool_max_size = pool_max_size
		self._exception_callback = exception_callback
		self._active_tasks = set()
		self._semaphore = asyncio.Semaphore(self._pool_max_size)
		self._event = asyncio.Event()
		self._pending = 0
		self._exception_count = 0

	@property
	def exception_count(self):
		return self._exception_count

	@property
	def slots_free(self):
		return self._pool_max_size - self._pending

	@property
	def pending(self):
		return self._pending

	async def _run_callable(self, task: "callable"):
		async with self._semaphore:
			try:
				await task
			except Exception as e:
				if self._exception_callback is not None:
					self._exception_callback(e)
				self._exception_count += 1
			finally:
				self._pending -= 1
				self._event.set()

	def submit(self, coroutine: "callable"):
		self._pending += 1
		task = asyncio.create_task(self._run_callable(coroutine))
		self._active_tasks.add(task)
		task.add_done_callback(self._active_tasks.discard)

	async def wait(self):
		while True:
			if self._pending == 0:
				break
			await self._event.wait()
			self._event.clear()

	async def __aenter__(self):
		return self

	async def __aexit__(self, *args):
		await self.wait()
