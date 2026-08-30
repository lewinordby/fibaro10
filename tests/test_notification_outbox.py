import os
import unittest
from unittest.mock import AsyncMock, patch


os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

import main


class NotificationOutboxTests(unittest.IsolatedAsyncioTestCase):
    def test_retry_delay_uses_capped_exponential_backoff(self) -> None:
        with (
            patch.object(main, "NTFY_OUTBOX_RETRY_BASE_SECONDS", 5),
            patch.object(main, "NTFY_OUTBOX_RETRY_MAX_SECONDS", 60),
        ):
            self.assertEqual(main.notification_retry_delay_seconds(1), 5)
            self.assertEqual(main.notification_retry_delay_seconds(2), 10)
            self.assertEqual(main.notification_retry_delay_seconds(9), 60)

    def test_light_payload_contains_event_context(self) -> None:
        event = main.OutdoorLightEvent(
            action="PAA",
            device_name="Fasade",
            lux=42,
            reason="regel",
        )

        payload = main.light_ntfy_payload(event)

        self.assertIsNotNone(payload)
        self.assertEqual(payload["topic"], main.NTFY_LIGHTS_TOPIC)
        self.assertIn("Fasade", payload["message"])
        self.assertIn("Lux: 42", payload["message"])

    async def test_publish_queues_without_calling_network(self) -> None:
        event = main.OutdoorLightEvent(action="AV", device_name="Fasade")
        with (
            patch("main.enqueue_ntfy_message", new=AsyncMock(return_value=True)) as enqueue,
            patch("main.publish_ntfy_message") as network,
        ):
            queued = await main.publish_light_ntfy(event)

        self.assertTrue(queued)
        enqueue.assert_awaited_once()
        network.assert_not_called()

    async def test_event_endpoint_passes_notification_to_atomic_save(self) -> None:
        payload = main.EventDataIn(
            system="lys",
            event_type="switch",
            action="PAA",
            device_name="Fasade",
            state=True,
        )
        with (
            patch.object(main.ingestion_http.dependencies, "save_record", new=AsyncMock(return_value=123)) as save,
            patch("main.publish_ntfy_message") as network,
        ):
            result = await main.log_event(payload)

        self.assertTrue(result["ntfy_queued"])
        self.assertEqual(result["id"], 123)
        self.assertEqual(save.await_args.kwargs["notification"]["topic"], main.NTFY_LIGHTS_TOPIC)
        network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
