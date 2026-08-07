from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class OperationalRetentionPolicy:
    access_success_days: int
    access_failure_days: int
    import_success_days: int
    import_failure_days: int
    notification_sent_days: int
    auth_session_days: int

    def cutoffs(self, now_value: datetime) -> dict[str, datetime]:
        return {
            "access_success": now_value - timedelta(days=self.access_success_days),
            "access_failure": now_value - timedelta(days=self.access_failure_days),
            "import_success": now_value - timedelta(days=self.import_success_days),
            "import_failure": now_value - timedelta(days=self.import_failure_days),
            "notification_sent": now_value - timedelta(days=self.notification_sent_days),
            "auth_session": now_value - timedelta(days=self.auth_session_days),
        }


async def execute_retention_statements(
    session_factory: Callable[[], Any],
    statements: Mapping[str, Any],
) -> dict[str, int]:
    deleted: dict[str, int] = {}
    async with session_factory() as session:
        for key, statement in statements.items():
            result = await session.execute(statement)
            deleted[key] = max(0, int(result.rowcount or 0))
        await session.commit()
    return deleted
