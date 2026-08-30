"""Control services with explicit process dependencies."""

from dataclasses import dataclass
from fastapi import HTTPException
from typing import Any
from typing import Any, Callable
from unifi_protect_client import ProtectLedgerClient
from unifi_protect_client import ProtectLedgerError
import asyncio


@dataclass
class Dependencies:
    UNIFI_PROTECT_API_TIMEOUT_SECONDS: Any
    UNIFI_PROTECT_EVENTS_URL: Any
    UNIFI_PROTECT_READ_API_TOKEN: Any


def create_service(dependencies: Dependencies):

    def protect_ledger_client() -> ProtectLedgerClient:
        UNIFI_PROTECT_API_TIMEOUT_SECONDS = dependencies.UNIFI_PROTECT_API_TIMEOUT_SECONDS
        UNIFI_PROTECT_EVENTS_URL = dependencies.UNIFI_PROTECT_EVENTS_URL
        UNIFI_PROTECT_READ_API_TOKEN = dependencies.UNIFI_PROTECT_READ_API_TOKEN
        if not UNIFI_PROTECT_READ_API_TOKEN:
            raise HTTPException(status_code=503, detail="UniFi Protect API token is not configured")
        return ProtectLedgerClient(
            UNIFI_PROTECT_EVENTS_URL,
            UNIFI_PROTECT_READ_API_TOKEN,
            UNIFI_PROTECT_API_TIMEOUT_SECONDS,
        )

    async def protect_ledger_json(method: str, **params: Any) -> dict[str, Any]:
        client = protect_ledger_client()
        try:
            return await asyncio.to_thread(getattr(client, method), **params)
        except ProtectLedgerError as error:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error

    def bollard_image_cache_control(kind: str, *, historical: bool = False) -> str:
        if historical:
            return "private, max-age=86400, immutable"
        if kind == "baseline":
            return "private, max-age=300"
        return "private, max-age=15, stale-while-revalidate=30"

    return {
        "bollard_image_cache_control": bollard_image_cache_control,
        "protect_ledger_client": protect_ledger_client,
        "protect_ledger_json": protect_ledger_json,
    }
