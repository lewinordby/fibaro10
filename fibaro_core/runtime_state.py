"""Explicit process-local state, instantiated only by application composition."""
from dataclasses import dataclass
from datetime import datetime
from asyncio import Lock


@dataclass
class IncidentState:
    bollard_failure_started_at: datetime | None = None


@dataclass
class ProcessLocks:
    sun2_axis_snapshot_link_lock: Lock | None = None
    sunroom_door_sync_lock: Lock | None = None
    met_weather_fetch_lock: Lock | None = None
    owntracks_visit_sync_lock: Lock | None = None
