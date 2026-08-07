import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any


AsyncHandler = Callable[[], Awaitable[None]]
TaskFactory = Callable[[], Awaitable[Any]]


class BackgroundTaskSupervisor:
    """Own long-running application tasks and stop them as one unit."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._tasks: dict[str, asyncio.Task[Any]] = {}

    def start(self, name: str, factory: TaskFactory) -> asyncio.Task[Any]:
        current = self._tasks.get(name)
        if current is not None and not current.done():
            return current

        task = asyncio.create_task(factory(), name=name)
        task.add_done_callback(lambda completed, task_name=name: self._task_finished(task_name, completed))
        self._tasks[name] = task
        return task

    def running_names(self) -> tuple[str, ...]:
        return tuple(name for name, task in self._tasks.items() if not task.done())

    async def stop_all(self) -> None:
        tasks = list(self._tasks.values())
        self._tasks.clear()
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _task_finished(self, name: str, task: asyncio.Task[Any]) -> None:
        if self._tasks.get(name) is task:
            self._tasks.pop(name, None)
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            self._logger.error(
                "Background task %s stopped unexpectedly",
                name,
                exc_info=(type(error), error, error.__traceback__),
            )


def create_lifespan(startup: AsyncHandler, shutdown: AsyncHandler):
    @asynccontextmanager
    async def lifespan(_app: Any) -> AsyncIterator[None]:
        try:
            await startup()
            yield
        finally:
            await shutdown()

    return lifespan
