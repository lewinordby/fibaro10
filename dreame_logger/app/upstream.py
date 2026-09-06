from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

from .normalization import normalize_device_snapshot
from .water_interlock import rewrite_schedule_states, schedule_state_map


LOGGER = logging.getLogger("dreame_logger.upstream")


@dataclass(frozen=True)
class DreameCredentials:
    username: str
    password: str
    country: str = "eu"
    account_type: str = "dreame"


class DreameUpstream:
    """Small standalone adapter around the pinned Dreame Vacuum protocol."""

    def __init__(
        self, credentials: DreameCredentials, timezone_name: str,
        on_telemetry: Callable[[dict[str, Any], str, str], None] | None = None,
    ) -> None:
        self.credentials = credentials
        self.timezone_name = timezone_name
        self.protocol: Any = None
        self.devices: dict[str, Any] = {}
        self.descriptors: dict[str, dict[str, Any]] = {}
        self.on_telemetry = on_telemetry
        self._observation_lock = threading.RLock()

    def _snapshot(self, device: Any, descriptor: dict[str, Any], reason: str, *, publish: bool = True) -> dict[str, Any]:
        with self._observation_lock:
            observed_at = datetime.now(ZoneInfo(self.timezone_name)).isoformat()
            snapshot = normalize_device_snapshot(device, descriptor, self.timezone_name)
            if publish and self.on_telemetry:
                self.on_telemetry(snapshot, observed_at, reason)
            return snapshot

    def publish_telemetry(self, external_ids: list[str]) -> None:
        for external_id in external_ids:
            self._snapshot(self.devices[external_id], self.descriptors[external_id], "periodic")

    def _listen_for_water_changes(self, device: Any, descriptor: dict[str, Any]) -> None:
        from dreame.types import DreameVacuumProperty

        def listener(property_name: str):
            def changed(previous: Any) -> None:
                if previous is None or not getattr(device, "_ready", False):
                    return
                try:
                    self._snapshot(device, descriptor, f"property:{property_name}")
                except Exception:
                    LOGGER.exception("Could not persist Dreame water change for %s", descriptor.get("did"))
            return changed

        for name in ("CLEAN_WATER_TANK_STATUS", "DIRTY_WATER_TANK_STATUS", "LOW_WATER_WARNING", "WATER_TANK"):
            device.listen(listener(name), getattr(DreameVacuumProperty, name))

    def _new_protocol(self, device_id: str | None = None, auth_key: str | None = None) -> Any:
        from dreame.protocol import DreameVacuumProtocol

        return DreameVacuumProtocol(
            username=self.credentials.username,
            password=self.credentials.password,
            country=self.credentials.country,
            prefer_cloud=True,
            account_type=self.credentials.account_type,
            device_id=device_id,
            auth_key=auth_key,
        )

    def discover(self) -> list[dict[str, Any]]:
        if self.protocol is None:
            self.protocol = self._new_protocol()
        if not self.protocol.cloud.logged_in and not self.protocol.cloud.login():
            raise RuntimeError("Innlogging mot Dreamehome feilet")
        response = self.protocol.cloud.get_devices() or {}
        records = ((response.get("page") or {}).get("records") or []) if isinstance(response, dict) else []
        descriptors: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict) or ".vacuum." not in str(record.get("model") or ""):
                continue
            descriptor = dict(record)
            descriptor["name"] = (
                descriptor.get("customName")
                or ((descriptor.get("deviceInfo") or {}).get("displayName"))
                or descriptor.get("model")
                or "Dreame"
            )
            external_id = str(descriptor.get("did") or "")
            if external_id:
                self.descriptors[external_id] = descriptor
                descriptors.append(descriptor)
        return descriptors

    def _device(self, descriptor: dict[str, Any]) -> Any:
        from dreame.device import DreameVacuumDevice

        external_id = str(descriptor.get("did") or "")
        if external_id in self.devices:
            return self.devices[external_id]
        device = DreameVacuumDevice(
            name=str(descriptor.get("name") or "Aqua10"),
            host=str(descriptor.get("bindDomain") or ""),
            token=" ",
            mac=descriptor.get("mac"),
            username=self.credentials.username,
            password=self.credentials.password,
            country=self.credentials.country,
            prefer_cloud=True,
            account_type=self.credentials.account_type,
            device_id=external_id,
        )
        # Map parsing is intentionally disabled. It is memory intensive and not
        # needed for reliable status, history or control in this service.
        device._map_manager = None
        if self.on_telemetry:
            self._listen_for_water_changes(device, descriptor)
        self.devices[external_id] = device
        return device

    def refresh(self) -> list[dict[str, Any]]:
        descriptors = self.discover()
        snapshots: list[dict[str, Any]] = []
        for descriptor in descriptors:
            external_id = str(descriptor.get("did") or "")
            try:
                device = self._device(descriptor)
                if not getattr(device, "available", False):
                    device.connect_device()
                device.update()
                snapshots.append(self._snapshot(device, descriptor, "periodic", publish=False))
            except Exception as exc:
                LOGGER.exception("Dreame refresh failed for %s", external_id)
                snapshots.append(
                    {
                        "provider": "dreame",
                        "external_id": external_id,
                        "duid": f"dreame:{external_id}",
                        "name": descriptor.get("name") or "Aqua10",
                        "model": descriptor.get("model"),
                        "metadata": {**descriptor, "provider": "dreame", "online": False},
                        "cloud": True,
                        "last_error": str(exc),
                    }
                )
        return snapshots

    def control(self, external_id: str, action: str) -> dict[str, Any]:
        descriptor = self.descriptors.get(external_id)
        if not descriptor:
            self.discover()
            descriptor = self.descriptors.get(external_id)
        if not descriptor:
            raise KeyError(external_id)
        device = self._device(descriptor)
        if not getattr(device, "available", False):
            device.connect_device()
        commands = {
            "start": device.start,
            "resume": device.start,
            "pause": device.pause,
            "stop": device.stop,
            "dock": device.return_to_base,
        }
        command = commands.get(action)
        if not command:
            raise ValueError(f"Ukjent Dreame-kommando: {action}")
        result = command()
        device.update()
        snapshot = normalize_device_snapshot(device, descriptor, self.timezone_name)
        return {"action": action, "result": result, "snapshot": snapshot}

    def set_schedule_states(self, external_id: str, requested: dict[str, str]) -> dict[str, Any]:
        from dreame.types import DreameVacuumProperty

        descriptor = self.descriptors.get(external_id)
        if not descriptor:
            self.discover()
            descriptor = self.descriptors.get(external_id)
        if not descriptor:
            raise KeyError(external_id)
        device = self._device(descriptor)
        if not getattr(device, "available", False):
            device.connect_device()
        device.update()
        raw_schedule = device.get_property(DreameVacuumProperty.SCHEDULE) or ""
        updated, before, changed = rewrite_schedule_states(raw_schedule, requested)
        if changed and not device.set_property(DreameVacuumProperty.SCHEDULE, updated):
            raise RuntimeError("Dreamehome avviste endring av vaskeplanene")
        if changed:
            device.update()
        verified = schedule_state_map(device.get_property(DreameVacuumProperty.SCHEDULE) or updated)
        failed = {
            schedule_id: {"expected": state, "actual": verified.get(schedule_id)}
            for schedule_id, state in requested.items()
            if schedule_id in before and verified.get(schedule_id) != state
        }
        return {
            "ok": not failed,
            "requested": requested,
            "before": before,
            "changed": changed,
            "verified": verified,
            "failed": failed,
        }

    def close(self) -> None:
        for device in self.devices.values():
            try:
                device.disconnect()
            except Exception:
                LOGGER.debug("Could not disconnect Dreame device", exc_info=True)
        if self.protocol:
            try:
                self.protocol.disconnect()
            except Exception:
                LOGGER.debug("Could not disconnect Dreame protocol", exc_info=True)
