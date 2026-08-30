"""Assets validation and public payloads."""

from datetime import datetime, timedelta
from typing import Any, Dict
from fibaro_core.models.system import AssetRegistryItem
from fibaro_core.schemas.system import AssetRegistryInput
from time_formatting import api_local_iso, normalize_local_naive


def asset_registry_payload(row: AssetRegistryItem) -> Dict[str, Any]:
    next_service_at = None
    if row.last_service_at and row.service_interval_days:
        next_service_at = row.last_service_at + timedelta(days=row.service_interval_days)
    return {
        "id": row.id,
        "navn": row.name,
        "kategori": row.category,
        "plassering": row.location or "",
        "produsent": row.manufacturer or "",
        "modell": row.model or "",
        "serienummer": row.serial_no or "",
        "HC3-ID": row.hc3_device_id,
        "eierapp": row.owner_app or "",
        "status": row.status,
        "installert": row.installed_at,
        "garanti til": row.warranty_until,
        "serviceintervall dager": row.service_interval_days,
        "sist vedlikehold": row.last_service_at,
        "neste vedlikehold": next_service_at,
        "notat": row.notes or "",
        "oppdatert": api_local_iso(normalize_local_naive(row.updated_at)),
    }


def apply_asset_registry_input(row: AssetRegistryItem, payload: AssetRegistryInput, now_dt: datetime) -> None:
    row.name = payload.name.strip()
    row.category = payload.category.strip()
    row.location = (payload.location or "").strip() or None
    row.manufacturer = (payload.manufacturer or "").strip() or None
    row.model = (payload.model or "").strip() or None
    row.serial_no = (payload.serial_no or "").strip() or None
    row.hc3_device_id = payload.hc3_device_id
    row.owner_app = (payload.owner_app or "").strip() or None
    row.status = payload.status.strip()
    row.installed_at = payload.installed_at
    row.warranty_until = payload.warranty_until
    row.service_interval_days = payload.service_interval_days
    row.last_service_at = payload.last_service_at
    row.notes = (payload.notes or "").strip() or None
    row.updated_at = now_dt
