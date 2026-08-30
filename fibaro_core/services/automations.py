"""Automations validation and public payloads."""

from datetime import datetime
import json
from typing import Any, Dict, Optional
from fibaro_core.models.system import AutomationWorkbenchRule
from fibaro_core.schemas.system import AutomationWorkbenchInput
from time_formatting import api_local_iso, normalize_local_naive


def workbench_json_text(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def automation_workbench_payload(row: AutomationWorkbenchRule) -> Dict[str, Any]:
    return {
        "id": row.id,
        "navn": row.name,
        "område": row.domain,
        "beskrivelse": row.description or "",
        "utløser": row.trigger_type,
        "trigger": workbench_json_text(row.trigger_config),
        "betingelser": workbench_json_text(row.conditions),
        "handlinger": workbench_json_text(row.actions),
        "modus": row.mode,
        "aktiv": bool(row.enabled),
        "ventetid min": row.cooldown_minutes,
        "sist evaluert": api_local_iso(normalize_local_naive(row.last_evaluated_at)),
        "sist utløst": api_local_iso(normalize_local_naive(row.last_triggered_at)),
        "siste resultat": row.last_result or "",
        "oppdatert": api_local_iso(normalize_local_naive(row.updated_at)),
    }


def workbench_config(value: Optional[str]) -> Dict[str, Any]:
    text_value = (value or "").strip()
    if not text_value:
        return {}
    try:
        parsed = json.loads(text_value)
        return parsed if isinstance(parsed, dict) else {"verdi": parsed}
    except json.JSONDecodeError:
        return {"beskrivelse": text_value}


def apply_automation_workbench_input(row: AutomationWorkbenchRule, payload: AutomationWorkbenchInput, now_dt: datetime) -> None:
    row.name = payload.name.strip()
    row.domain = payload.domain.strip()
    row.description = (payload.description or "").strip() or None
    row.trigger_type = payload.trigger_type.strip()
    row.trigger_config = workbench_config(payload.trigger)
    row.conditions = workbench_config(payload.conditions)
    row.actions = workbench_config(payload.actions)
    row.mode = payload.mode.strip()
    row.enabled = payload.enabled
    row.cooldown_minutes = payload.cooldown_minutes
    row.updated_at = now_dt
