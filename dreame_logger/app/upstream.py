from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .normalization import normalize_device_snapshot


LOGGER = logging.getLogger("dreame_logger.upstream")


@dataclass(frozen=True)
class DreameCredentials:
    username: str
    password: str
    country: str = "eu"
    account_type: str = "dreame"


class DreameUpstream:
    """Small standalone adapter around the pinned Dreame Vacuum protocol."""

    def __init__(self, credentials: DreameCredentials, timezone_name: str) -> None:
        self.credentials = credentials
        self.timezone_name = timezone_name
        self.protocol: Any = None
        self.devices: dict[str, Any] = {}
        self.descriptors: dict[str, dict[str, Any]] = {}

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
                snapshots.append(normalize_device_snapshot(device, descriptor, self.timezone_name))
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
