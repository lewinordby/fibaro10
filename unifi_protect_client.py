from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


@dataclass
class ProtectLedgerError(RuntimeError):
    message: str
    status_code: int = 502

    def __str__(self) -> str:
        return self.message


class ProtectLedgerClient:
    def __init__(self, base_url: str, token: str, timeout_seconds: float = 10):
        self.base_url = base_url.rstrip("/")
        self.token = token.strip()
        self.timeout_seconds = timeout_seconds

    def _request(self, path: str, params: Optional[Mapping[str, Any]] = None) -> tuple[bytes, str]:
        query_items = {
            key: value
            for key, value in (params or {}).items()
            if value is not None and value != ""
        }
        query = urlencode(query_items, doseq=True)
        url = f"{self.base_url}{path}{'?' + query if query else ''}"
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            with urlopen(Request(url, headers=headers), timeout=self.timeout_seconds) as response:
                return response.read(), response.headers.get_content_type()
        except HTTPError as error:
            detail = f"Protect Ledger returned HTTP {error.code}"
            try:
                payload = json.loads(error.read().decode("utf-8"))
                detail = str(payload.get("detail") or detail)
            except (ValueError, UnicodeDecodeError):
                pass
            status = error.code if error.code in {400, 401, 403, 404, 422} else 502
            raise ProtectLedgerError(detail, status) from error
        except (URLError, TimeoutError, OSError) as error:
            raise ProtectLedgerError(f"Protect Ledger is unavailable: {error}", 503) from error

    def get_json(self, path: str, params: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
        content, _ = self._request(path, params)
        try:
            payload = json.loads(content.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as error:
            raise ProtectLedgerError("Protect Ledger returned invalid JSON", 502) from error
        if not isinstance(payload, dict):
            raise ProtectLedgerError("Protect Ledger returned an unexpected response", 502)
        return payload

    def status(self) -> dict[str, Any]:
        return self.get_json("/api/v1/status")

    def cameras(self) -> dict[str, Any]:
        return self.get_json("/api/v1/cameras")

    def capabilities(self) -> dict[str, Any]:
        return self.get_json("/api/v1/capabilities")

    def stats(self) -> dict[str, Any]:
        return self.get_json("/api/v1/stats")

    def events(self, **params: Any) -> dict[str, Any]:
        return self.get_json("/api/v1/events", params)

    def recognitions(self, **params: Any) -> dict[str, Any]:
        return self.get_json("/api/v1/recognitions", params)

    def daily_license_plates(self, **params: Any) -> dict[str, Any]:
        return self.get_json("/api/v1/license-plates/daily", params)

    def bollards(self) -> dict[str, Any]:
        return self.get_json("/api/v1/bollards")

    def recognition_detail(self, recognition_id: int) -> dict[str, Any]:
        return self.get_json(f"/api/v1/recognitions/{recognition_id}")

    def snapshot(self, source_event_id: str) -> tuple[bytes, str]:
        return self._request(f"/api/v1/events/{quote(source_event_id, safe='')}/snapshot")

    def recognition_snapshot(self, recognition_id: int) -> tuple[bytes, str]:
        return self._request(f"/api/v1/recognitions/{recognition_id}/snapshot")

    def bollard_region_baseline(self, region_id: int) -> tuple[bytes, str]:
        return self._request(f"/api/v1/bollards/regions/{region_id}/baseline")

    def bollard_camera_image(self, camera_id: str, kind: str) -> tuple[bytes, str]:
        if kind not in {"baseline", "latest", "overlay", "ai"}:
            raise ProtectLedgerError("Unsupported bollard camera image kind", 400)
        return self._request(
            f"/api/v1/bollards/cameras/{quote(camera_id, safe='')}/{kind}"
        )

    def bollard_camera_crop(self, camera_id: str, kind: str) -> tuple[bytes, str]:
        if kind not in {"baseline", "latest", "overlay"}:
            raise ProtectLedgerError("Unsupported bollard camera image kind", 400)
        return self._request(
            f"/api/v1/bollards/cameras/{quote(camera_id, safe='')}/{kind}/crop"
        )

    def bollard_asset_image(self, asset_key: str, kind: str) -> tuple[bytes, str]:
        if kind not in {"baseline", "latest", "overlay", "ai"}:
            raise ProtectLedgerError("Unsupported monitored asset image kind", 400)
        return self._request(
            f"/api/v1/bollards/assets/{quote(asset_key, safe='')}/{kind}"
        )

    def bollard_incident_image(
        self,
        incident_id: int,
        camera_id: str,
        kind: str,
    ) -> tuple[bytes, str]:
        return self._request(
            f"/api/v1/bollards/incidents/{incident_id}/images/"
            f"{quote(camera_id, safe='')}/{quote(kind, safe='')}"
        )
