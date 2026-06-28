from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo
import re

from dateutil import parser as dtparser
from sqlalchemy import func

LOCAL_TZ = ZoneInfo("Europe/Oslo")


def _normalize_local_naive(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return value.replace(tzinfo=None)


def _local_now_naive() -> datetime:
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)


def normalize_plate(value: Optional[str]) -> str:
    return re.sub(r"\s+", "", (value or "").strip().upper())


def compact_plate(value: Optional[str]) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value or "").upper()


def compact_plate_sql(column):
    return func.upper(func.regexp_replace(column, r"[^A-Za-z0-9]", "", "g"))


SWEDISH_LICENSE_PLATE_REGEX = re.compile(r"^[A-HJ-PR-UW-Z]{3}[0-9]{2}([0-9]|[A-HJ-NPR-UW-Z])$")
SWEDISH_LICENSE_PLATE_SQL_REGEX = r"^[A-HJ-PR-UW-Z]{3}[0-9]{2}([0-9]|[A-HJ-NPR-UW-Z])$"
DANISH_LICENSE_PLATE_REGEX = re.compile(r"^[A-Z]{2}[0-9]{5}$")
DANISH_LICENSE_PLATE_SQL_REGEX = r"^[A-Z]{2}[0-9]{5}$"


def is_swedish_license_plate(value: Optional[str]) -> bool:
    return bool(SWEDISH_LICENSE_PLATE_REGEX.fullmatch(compact_plate(value)))


def is_danish_license_plate(value: Optional[str]) -> bool:
    return bool(DANISH_LICENSE_PLATE_REGEX.fullmatch(compact_plate(value)))


def foreign_plate_country_code(value: Optional[str]) -> Optional[str]:
    compact = compact_plate(value)
    if is_swedish_license_plate(compact):
        return "S"
    if is_danish_license_plate(compact):
        return "DK"
    return None


def is_supported_foreign_license_plate(value: Optional[str]) -> bool:
    return foreign_plate_country_code(value) is not None


CAR_INFO_IMPORT_JOB_BY_COUNTRY = {
    "S": "parking_vehicle_biluppgifter_sync",
    "DK": "parking_vehicle_tjekbil_sync",
}


def car_info_lookup_country_code(data: Optional[Dict[str, Any]], plate: Optional[str] = None) -> str:
    country_code = car_info_country_code(data)
    if country_code:
        return country_code
    return foreign_plate_country_code(plate) or ""


def car_info_import_job_name(data: Optional[Dict[str, Any]], plate: Optional[str] = None) -> str:
    country_code = car_info_lookup_country_code(data, plate)
    return CAR_INFO_IMPORT_JOB_BY_COUNTRY.get(country_code, "parking_vehicle_biluppgifter_sync")


def car_info_import_ok(status: Optional[int]) -> bool:
    return status in {200, 204, 404}


def car_info_source_label(data: Optional[Dict[str, Any]], plate: Optional[str] = None) -> str:
    provider = car_info_provider_label(data)
    if provider != "utenlandsk kilde":
        return provider
    country_code = car_info_lookup_country_code(data, plate)
    if country_code == "S":
        return "Biluppgifter.se"
    if country_code == "DK":
        return "Tjekbil.dk"
    return provider


def car_info_fields(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    fields = data.get("fields")
    return fields if isinstance(fields, dict) else {}


def car_info_confirmed_swedish(data: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(data, dict):
        return False
    country_code = str(data.get("country_code") or "").upper()
    return bool(data.get("confirmed_swedish") or (country_code == "S" and data.get("confirmed_vehicle")))


def car_info_country_code(data: Optional[Dict[str, Any]]) -> str:
    return str((data or {}).get("country_code") or "").strip().upper() if isinstance(data, dict) else ""


def car_info_confirmed_foreign(data: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(data, dict):
        return False
    return bool(data.get("confirmed_vehicle") or data.get("confirmed_swedish") or data.get("confirmed_danish"))


def car_info_area_label(data: Optional[Dict[str, Any]]) -> Optional[str]:
    country_code = car_info_country_code(data)
    if country_code == "S":
        return "Sverige"
    if country_code == "DK":
        return "Danmark"
    return None


def car_info_vehicle_title(data: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    fields = car_info_fields(data)
    return first_value(fields.get("vehicle_title"), data.get("vehicle_title"), data.get("title"))


def car_info_field_value(data: Optional[Dict[str, Any]], *keys: str) -> Any:
    fields = car_info_fields(data)
    for key in keys:
        value = fields.get(key)
        if value not in (None, ""):
            return value
    return None


def car_info_provider_label(data: Optional[Dict[str, Any]]) -> str:
    provider = str((data or {}).get("provider") or "").strip().lower() if isinstance(data, dict) else ""
    if provider == "biluppgifter":
        return "Biluppgifter.se"
    if provider == "tjekbil":
        return "Tjekbil.dk"
    return "utenlandsk kilde"


def car_info_status_label(status: Optional[int], data: Optional[Dict[str, Any]] = None) -> str:
    if status == 200:
        area = car_info_area_label(data)
        return f"Bekreftet {area.lower()}" if area and car_info_confirmed_foreign(data) else "Hentet"
    if status == 204:
        return "Ingen treff"
    if status == 404:
        return "Ikke funnet"
    if status == 429:
        return "Rate-limit"
    if status:
        return f"HTTP {status}"
    return "-"


def first_value(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def data_path(data: Any, *path: Any) -> Any:
    current = data
    for key in path:
        if current is None:
            return None
        if isinstance(key, int):
            if not isinstance(current, list) or len(current) <= key:
                return None
            current = current[key]
        elif isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current


def code_text(value: Any) -> Any:
    if isinstance(value, dict):
        return first_value(value.get("kodeNavn"), value.get("kodeBeskrivelse"), value.get("kodeVerdi"))
    return value


def parse_int_value(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return None


def parse_float_value(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def parse_date_value(value: Any) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def parse_svv_datetime_value(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return _normalize_local_naive(value)
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    try:
        parsed = dtparser.parse(str(value))
    except (TypeError, ValueError, OverflowError):
        return None
    return _normalize_local_naive(parsed)


def first_vehicle_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    vehicles = raw.get("kjoretoydataListe")
    if isinstance(vehicles, list) and vehicles:
        return vehicles[0] if isinstance(vehicles[0], dict) else {}
    return raw if isinstance(raw, dict) else {}


def svv_current_ownership_at(raw: Optional[Dict[str, Any]]) -> Optional[datetime]:
    if not raw:
        return None
    vehicle = first_vehicle_data(raw)
    return parse_svv_datetime_value(
        first_value(
            data_path(vehicle, "registrering", "registrertForstegangPaEierskap"),
            data_path(vehicle, "registrering", "registrertForstegangPaaEierskap"),
            data_path(vehicle, "registrering", "registrertForstegangPåEierskap"),
        )
    )


def svv_detail_values(plate: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    vehicle = first_vehicle_data(raw)
    tech = data_path(vehicle, "godkjenning", "tekniskGodkjenning")
    data = data_path(tech, "tekniskeData") or {}
    generelt = data_path(data, "generelt") or {}
    klassifisering = data_path(tech, "kjoretoyklassifisering") or {}
    weights = data_path(data, "vekter") or {}
    dimensions = data_path(data, "dimensjoner") or {}
    personer = data_path(data, "persontall") or {}
    miljodata = data_path(data, "miljodata") or {}
    motor = data_path(data, "motorOgDrivverk", "motor") or []
    motor0 = motor[0] if isinstance(motor, list) and motor else {}
    color = first_value(
        code_text(data_path(data, "karosseriOgLasteplan", "rFarge", 0)),
        code_text(data_path(data, "karosseriOgLasteplan", "farge", 0)),
    )
    return {
        "plate": compact_plate(plate),
        "vin": data_path(vehicle, "kjoretoyId", "understellsnummer"),
        "merke": first_value(
            data_path(generelt, "merke", 0, "merke"),
            data_path(generelt, "merke", 0, "merkeNavn"),
            data_path(generelt, "merke", 0),
        ),
        "modell": first_value(
            data_path(generelt, "handelsbetegnelse", 0),
            data_path(generelt, "modell"),
        ),
        "typebetegnelse": data_path(generelt, "typebetegnelse"),
        "kjoretoyklasse_kode": data_path(klassifisering, "tekniskKode", "kodeVerdi"),
        "kjoretoyklasse_navn": code_text(data_path(klassifisering, "tekniskKode")),
        "registreringsstatus_kode": data_path(vehicle, "registrering", "registreringsstatus", "kodeVerdi"),
        "registreringsstatus_tekst": code_text(data_path(vehicle, "registrering", "registreringsstatus")),
        "forstegangsregistrert_norge": parse_date_value(data_path(vehicle, "forstegangsregistrering", "registrertForstegangNorgeDato")),
        "pkk_kontrollfrist": parse_date_value(data_path(vehicle, "periodiskKjoretoyKontroll", "kontrollfrist")),
        "egenvekt_kg": parse_int_value(first_value(data_path(weights, "egenvekt"), data_path(weights, "egenvektMinimum"))),
        "nyttelast_kg": parse_int_value(data_path(weights, "nyttelast")),
        "tillatt_totalvekt_kg": parse_int_value(data_path(weights, "tillattTotalvekt")),
        "tillatt_vogntogvekt_kg": parse_int_value(data_path(weights, "tillattVogntogvekt")),
        "tillatt_tilhengervekt_med_brems_kg": parse_int_value(data_path(weights, "tillattTilhengervektMedBrems")),
        "tillatt_tilhengervekt_uten_brems_kg": parse_int_value(data_path(weights, "tillattTilhengervektUtenBrems")),
        "seter_totalt": parse_int_value(first_value(data_path(personer, "sitteplasserTotalt"), data_path(personer, "sitteplasserForan"))),
        "lengde_mm": parse_int_value(data_path(dimensions, "lengde")),
        "bredde_mm": parse_int_value(data_path(dimensions, "bredde")),
        "hoyde_mm": parse_int_value(data_path(dimensions, "hoyde")),
        "rekkevidde_wltp_km": parse_int_value(data_path(miljodata, "wltpKjoretoyspesifikk", "rekkeviddeKm")),
        "elforbruk_wltp_wh_km": parse_int_value(data_path(miljodata, "wltpKjoretoyspesifikk", "elforbrukWhPerKm")),
        "motoreffekt_samlet_kw": parse_float_value(data_path(motor0, "drivstoff", 0, "maksEffektPrTime")),
        "motoreffekt_kontinuerlig_kw": parse_float_value(data_path(motor0, "drivstoff", 0, "maksNettoEffekt")),
        "maks_hastighet_kmt": parse_int_value(data_path(data, "maksimumHastighet", "hastighet")),
        "stoy_db": parse_int_value(data_path(data, "miljodata", "stoy", "standstoy")),
        "abs": data_path(data, "bremser", "abs"),
        "farge": color,
        "svv_godkjennings_id": first_value(
            data_path(tech, "godkjenningsId"),
            data_path(vehicle, "godkjenning", "forstegangsGodkjenning", "godkjenningsId"),
        ),
        "svv_teknisk_gyldig_fra": parse_date_value(first_value(data_path(tech, "gyldigFraDato"), data_path(tech, "gyldigFraDatoTid"))),
        "sist_synkronisert": datetime.utcnow(),
    }


def parking_slot_remainder_minutes(row: ParkingSession) -> Optional[int]:
    duration = row.parking_time_min
    if duration is None and row.start_time and row.end_time:
        duration = (row.end_time - row.start_time).total_seconds() / 60
    if duration is None or duration <= 0:
        return None
    remainder = duration % 30
    if remainder < 1 or remainder > 29:
        return None
    return int(round(30 - remainder))


def parking_vehicle_year(details: Optional[ParkingVehicleDetails]) -> Optional[int]:
    if not details:
        return None
    source = details.forstegangsregistrert_norge or details.svv_teknisk_gyldig_fra
    return source.year if source else None


def parking_vehicle_label(details: Optional[ParkingVehicleDetails]) -> str:
    if not details:
        return "Ukjent kjøretøy"
    text = " ".join(part for part in [details.merke, details.modell, details.typebetegnelse] if part)
    return text or "Ukjent kjøretøy"


def parking_vehicle_label_is_unknown(value: Optional[str]) -> bool:
    text_value = (value or "").strip().lower()
    return not text_value or text_value.startswith("ukjent")


def car_info_model_year(data: Optional[Dict[str, Any]]) -> Optional[int]:
    for value in [
        car_info_field_value(data, "model_year"),
        car_info_field_value(data, "first_registered", "first_registration"),
    ]:
        match = re.search(r"(19|20)\d{2}", str(value or ""))
        if match:
            return int(match.group(0))
    return None


def parking_vehicle_display_label(details: Optional[ParkingVehicleDetails], car_info_data: Optional[Dict[str, Any]] = None) -> str:
    label = parking_vehicle_label(details)
    if not parking_vehicle_label_is_unknown(label):
        return label
    return car_info_vehicle_title(car_info_data) or label


def parking_vehicle_display_source(details: Optional[ParkingVehicleDetails], car_info_data: Optional[Dict[str, Any]] = None) -> str:
    if not parking_vehicle_label_is_unknown(parking_vehicle_label(details)):
        return "Fra SVV"
    if car_info_vehicle_title(car_info_data):
        return f"Fra {car_info_provider_label(car_info_data)}"
    return ""


def parking_vehicle_display_year(details: Optional[ParkingVehicleDetails], car_info_data: Optional[Dict[str, Any]] = None) -> Optional[int]:
    return parking_vehicle_year(details) or car_info_model_year(car_info_data)


def parking_vehicle_display_color(details: Optional[ParkingVehicleDetails], car_info_data: Optional[Dict[str, Any]] = None) -> Any:
    return first_value(details.farge if details else None, car_info_field_value(car_info_data, "color"))


def parking_vehicle_display_class(details: Optional[ParkingVehicleDetails], car_info_data: Optional[Dict[str, Any]] = None) -> Any:
    return first_value(
        details.kjoretoyklasse_navn if details else None,
        car_info_field_value(car_info_data, "vehicle_type", "classification"),
    )


def parking_vehicle_display_registration_status(
    details: Optional[ParkingVehicleDetails],
    car_info_data: Optional[Dict[str, Any]] = None,
) -> Any:
    return first_value(
        details.registreringsstatus_tekst if details else None,
        car_info_field_value(car_info_data, "registration_status"),
    )


def parking_vehicle_display_inspection_deadline(
    details: Optional[ParkingVehicleDetails],
    car_info_data: Optional[Dict[str, Any]] = None,
) -> Any:
    return first_value(
        details.pkk_kontrollfrist if details else None,
        car_info_field_value(car_info_data, "inspection_valid_to", "next_inspection"),
    )


def parking_vehicle_summary(details: Optional[ParkingVehicleDetails], car_info_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
    label = parking_vehicle_display_label(details, car_info_data)
    if parking_vehicle_label_is_unknown(label):
        return None
    year = parking_vehicle_display_year(details, car_info_data)
    summary = f"{year} {label}" if year else label
    color = str(parking_vehicle_display_color(details, car_info_data) or "").strip()
    return f"{summary} - {color}" if color else summary


def parking_source_label(source_system: Optional[str]) -> str:
    return (source_system or "").strip() or "-"


def parking_duration_minutes(row: ParkingSession, now: Optional[datetime] = None) -> Optional[float]:
    if row.parking_time_min is not None:
        return row.parking_time_min
    if row.start_time and row.end_time:
        return max(0, (row.end_time - row.start_time).total_seconds() / 60)
    if row.start_time and (row.status or "").strip().lower() == "ongoing":
        now = now or _local_now_naive()
        return max(0, (now - row.start_time).total_seconds() / 60)
    return None


def parking_day_time_label(value: Optional[datetime], selected_day: date) -> str:
    if not value:
        return "-"
    offset = (value.date() - selected_day).days
    suffix = f" {offset:+d}" if offset else ""
    return f"{value.strftime('%H:%M')}{suffix}"


def parking_current_ownership_warning(
    vehicle: Optional[ParkingVehicle],
    observed_at: Optional[datetime],
) -> Optional[Dict[str, Any]]:
    ownership_at = svv_current_ownership_at(vehicle.svv_data if vehicle else None)
    observed_at = _normalize_local_naive(observed_at)
    if not ownership_at or not observed_at or observed_at >= ownership_at:
        return None
    return {
        "ownership_at": ownership_at,
        "text": (
            f"OBS: Parkeringen er før nåværende eierskap i SVV "
            f"({ownership_at.strftime('%d.%m.%Y')}). Navn/område kan gjelde ny eier."
        ),
    }


def parking_row_context(
    row: ParkingSession,
    vehicle: Optional[ParkingVehicle] = None,
    details: Optional[ParkingVehicleDetails] = None,
    now: Optional[datetime] = None,
    selected_day: Optional[date] = None,
) -> Dict[str, Any]:
    plate = normalize_plate(row.car_license_number)
    selected_day = selected_day or _local_now_naive().date()
    return {
        "session": row,
        "plate": plate,
        "vehicle_name": vehicle.navn if vehicle else None,
        "vehicle_area": vehicle.omrade if vehicle else None,
        "vehicle_title": parking_vehicle_summary(details, vehicle.car_info_data if vehicle else None),
        "source_label": parking_source_label(row.source_system),
        "parking_count": vehicle.parkering_count if vehicle else None,
        "duration_minutes": parking_duration_minutes(row, now),
        "start_label": parking_day_time_label(row.start_time, selected_day),
        "end_label": parking_day_time_label(row.end_time, selected_day),
        "owner_warning": parking_current_ownership_warning(vehicle, row.start_time),
    }
