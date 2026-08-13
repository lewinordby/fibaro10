from datetime import date, datetime, time, timedelta
from typing import Any, Iterable, Mapping


def parse_clock(value: Any, fallback: time) -> time:
    try:
        hour_text, minute_text = str(value).strip().split(":", 1)
        return time(hour=int(hour_text), minute=int(minute_text))
    except (TypeError, ValueError):
        return fallback


def opening_window(
    selected_day: date,
    open_from: Any = "07:00",
    close_at: Any = "23:00",
) -> tuple[datetime, datetime]:
    start = datetime.combine(selected_day, parse_clock(open_from, time(hour=7)))
    end = datetime.combine(selected_day, parse_clock(close_at, time(hour=23)))
    if end <= start:
        end = datetime.combine(selected_day, time(hour=23))
    return start, end


def automation_counter_start(
    open_at: datetime,
    last_started_at: datetime | None,
    counter_reset_at: datetime | None,
) -> datetime:
    candidates = [open_at]
    for value in (last_started_at, counter_reset_at):
        if value and value.date() == open_at.date():
            candidates.append(value)
    return max(candidates)


def unique_ints(values: Iterable[Any]) -> list[int]:
    result: list[int] = []
    for value in values:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0 and parsed not in result:
            result.append(parsed)
    return result


def automation_decision(
    *,
    now: datetime,
    enabled: bool,
    open_at: datetime,
    close_at: datetime,
    opening_count: int,
    opening_threshold: int,
    minimum_interval_minutes: int,
    last_started_at: datetime | None,
    door_is_open: bool | None,
    validation_issues: Iterable[str] = (),
    status: str | None = None,
    last_attempt_at: datetime | None = None,
    retry_minutes: int = 5,
) -> dict[str, Any]:
    issues = [str(issue) for issue in validation_issues if str(issue).strip()]
    next_allowed_at = (
        last_started_at + timedelta(minutes=minimum_interval_minutes) if last_started_at else None
    )
    remaining_interval_seconds = (
        max(0, int((next_allowed_at - now).total_seconds()))
        if next_allowed_at and now < next_allowed_at
        else 0
    )
    retry_at = last_attempt_at + timedelta(minutes=retry_minutes) if last_attempt_at else None

    if not enabled:
        key, label, detail = "disabled", "Deaktivert", "Automatikken starter ikke roboten."
    elif issues:
        key, label, detail = "configuration_error", "Mangler oppsett", issues[0]
    elif not (open_at <= now < close_at):
        key, label, detail = (
            "outside_hours",
            "Utenfor åpningstid",
            "Dagens telling brukes ikke utenfor åpningstiden.",
        )
    elif (
        status == "starting"
        and last_attempt_at is not None
        and now - last_attempt_at < timedelta(minutes=2)
    ):
        key, label, detail = "starting", "Starter renhold", "Kommandoen sendes til roboten."
    elif opening_count < opening_threshold:
        missing = opening_threshold - opening_count
        key, label, detail = (
            "counting",
            "Teller åpninger",
            f"Mangler {missing} åpning" if missing == 1 else f"Mangler {missing} åpninger",
        )
    elif door_is_open is True:
        key, label, detail = "door_open", "Inngangsdøren er åpen", "Venter til døren er lukket."
    elif remaining_interval_seconds > 0:
        remaining_minutes = max(1, (remaining_interval_seconds + 59) // 60)
        key, label, detail = (
            "minimum_interval",
            "Venter på automatisk start",
            f"Terskelen er nådd. Starter automatisk om {remaining_minutes} min.",
        )
    elif status == "error" and retry_at and now < retry_at:
        remaining_minutes = max(1, int(((retry_at - now).total_seconds() + 59) // 60))
        key, label, detail = "retry_wait", "Venter før nytt forsøk", f"Nytt forsøk om {remaining_minutes} min."
    else:
        key, label, detail = "ready", "Klar til start", "Alle vilkår er oppfylt."

    return {
        "key": key,
        "label": label,
        "detail": detail,
        "eligible": key == "ready",
        "pending": key in {"minimum_interval", "door_open", "retry_wait"} and opening_count >= opening_threshold,
        "next_allowed_at": next_allowed_at,
        "remaining_interval_seconds": remaining_interval_seconds,
        "retry_at": retry_at,
    }


def profile_command_payload(profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": int(profile["id"]),
        "name": str(profile["name"]),
        "cleaning_type": str(profile["cleaningType"]),
        "fan_power": int(profile["fanPower"]),
        "water_box_mode": int(profile["waterBoxMode"]),
        "mop_mode": int(profile["mopMode"]),
        "repeat": int(profile["repeat"]),
        "summary": str(profile["summary"]),
    }
