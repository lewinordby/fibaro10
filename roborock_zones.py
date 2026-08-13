from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class RoborockZoneCandidate:
    zone_number: int
    segment_id: str
    schedule_id: str
    cron: str


class RoborockZoneScheduleError(ValueError):
    pass


def _value(schedule: Any, key: str) -> Any:
    if isinstance(schedule, Mapping):
        return schedule.get(key)
    return getattr(schedule, key, None)


def _is_disabled(value: Any) -> bool:
    if value is False or value == 0:
        return True
    return str(value or "").strip().lower() in {"false", "off", "no"}


def _segment_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = [value]
    return [str(item).strip() for item in values if str(item).strip()]


def discover_roborock_zone_candidates(schedules: Iterable[Any]) -> list[RoborockZoneCandidate]:
    candidates: list[RoborockZoneCandidate] = []
    errors: list[str] = []
    for schedule in schedules:
        cron = str(_value(schedule, "cron") or "").strip()
        cron_parts = cron.split()
        if len(cron_parts) < 2 or not cron_parts[0].isdigit() or not cron_parts[1].isdigit():
            continue
        minute = int(cron_parts[0])
        hour = int(cron_parts[1])
        if hour != 12 or not 1 <= minute <= 59 or not _is_disabled(_value(schedule, "enabled")):
            continue

        schedule_id = str(_value(schedule, "schedule_id") or _value(schedule, "id") or "-")
        segment_value = _value(schedule, "segments")
        if segment_value is None and isinstance(schedule, Mapping):
            params = ((schedule.get("param") or {}).get("params") or [])
            if params and isinstance(params[0], Mapping):
                segment_value = params[0].get("segments")
        segments = _segment_ids(segment_value)
        if len(segments) != 1:
            errors.append(
                f"Plan {schedule_id} kl. 12:{minute:02d} må inneholde nøyaktig ett segment, fant {len(segments)}"
            )
            continue
        candidates.append(
            RoborockZoneCandidate(
                zone_number=minute,
                segment_id=segments[0],
                schedule_id=schedule_id,
                cron=cron,
            )
        )

    by_zone: dict[int, RoborockZoneCandidate] = {}
    by_segment: dict[str, RoborockZoneCandidate] = {}
    for candidate in candidates:
        previous_zone = by_zone.get(candidate.zone_number)
        if previous_zone and previous_zone.segment_id != candidate.segment_id:
            errors.append(
                f"Sone {candidate.zone_number} finnes med både segment {previous_zone.segment_id} og {candidate.segment_id}"
            )
        previous_segment = by_segment.get(candidate.segment_id)
        if previous_segment and previous_segment.zone_number != candidate.zone_number:
            errors.append(
                f"Segment {candidate.segment_id} er brukt for både Sone {previous_segment.zone_number} og Sone {candidate.zone_number}"
            )
        by_zone[candidate.zone_number] = candidate
        by_segment[candidate.segment_id] = candidate

    if errors:
        raise RoborockZoneScheduleError("; ".join(errors))
    return sorted(by_zone.values(), key=lambda item: item.zone_number)
