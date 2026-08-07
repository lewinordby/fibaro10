import asyncio
import logging
import unittest

from application_lifecycle import BackgroundTaskSupervisor, create_lifespan


class ApplicationLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_supervisor_starts_each_named_task_once_and_stops_all(self) -> None:
        supervisor = BackgroundTaskSupervisor(logging.getLogger("lifecycle-test"))
        started = asyncio.Event()
        stopped = asyncio.Event()

        async def worker() -> None:
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()

        first = supervisor.start("worker", worker)
        second = supervisor.start("worker", worker)
        await started.wait()

        self.assertIs(first, second)
        self.assertEqual(supervisor.running_names(), ("worker",))

        await supervisor.stop_all()

        self.assertTrue(stopped.is_set())
        self.assertEqual(supervisor.running_names(), ())

    async def test_lifespan_always_runs_shutdown(self) -> None:
        calls: list[str] = []

        async def startup() -> None:
            calls.append("startup")

        async def shutdown() -> None:
            calls.append("shutdown")

        lifespan = create_lifespan(startup, shutdown)
        async with lifespan(object()):
            calls.append("running")

        self.assertEqual(calls, ["startup", "running", "shutdown"])


if __name__ == "__main__":
    unittest.main()
