import asyncio
import base64
import datetime as dt
import hashlib
import html
import json
import logging
import os
import pickle
import secrets
import string
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query, status as http_status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

load_dotenv()

DATA_DIR = Path(os.getenv("ROBOROCK_DATA_DIR", "./data"))
CACHE_FILE = DATA_DIR / "roborock_user_data.pickle"
CLIENT_IDS_FILE = DATA_DIR / "roborock_client_ids.json"
HOME_CACHE_FILE = DATA_DIR / "home_data.json"
STATE_FILE = DATA_DIR / "state.json"
QUEUE_FILE = DATA_DIR / "pending_batches.jsonl"
CONTROL_LOG_FILE = DATA_DIR / "control_commands.jsonl"

ROBOROCK_EMAIL = os.getenv("ROBOROCK_EMAIL", "roborock.sun2@gmail.com")
ROBOROCK_SUBNET = os.getenv("ROBOROCK_SUBNET", "192.168.2.")
COLLECTOR_ID = os.getenv("COLLECTOR_ID", "roborock_logger")
LOCAL_TIMEZONE = os.getenv("LOCAL_TIMEZONE", "Europe/Oslo")
LOCAL_TZ = ZoneInfo(LOCAL_TIMEZONE)
FIBARO10_API_BASE_URL = os.getenv("FIBARO10_API_BASE_URL", "http://fibaro10:8110").rstrip("/")
FIBARO10_API_USERNAME = os.getenv("FIBARO10_API_USERNAME", "")
FIBARO10_API_PASSWORD = os.getenv("FIBARO10_API_PASSWORD", "")
STATUS_INTERVAL_SECONDS = int(os.getenv("STATUS_INTERVAL_SECONDS", "300"))
TELEMETRY_INTERVAL_SECONDS = int(os.getenv("TELEMETRY_INTERVAL_SECONDS", "60"))
TELEMETRY_SETTINGS_INTERVAL_SECONDS = int(os.getenv("TELEMETRY_SETTINGS_INTERVAL_SECONDS", "900"))
HOME_REFRESH_SECONDS = int(os.getenv("HOME_REFRESH_SECONDS", "3600"))
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "10"))
MAP_SYNC_ON_START = os.getenv("MAP_SYNC_ON_START", "true").lower() in {"1", "true", "yes", "on"}
AUTO_SYNC_ENABLED = os.getenv("AUTO_SYNC_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
ROBOROCK_CONTROL_TOKEN = os.getenv("ROBOROCK_CONTROL_TOKEN", "").strip()
ROBOROCK_LOCAL_PORT = 58867

app = FastAPI(title="Roborock_logger")
sync_lock = asyncio.Lock()
telemetry_unsupported_commands: dict[str, set[str]] = {}
telemetry_last_settings_at: dict[str, float] = {}


class ControlRequest(BaseModel):
    action: Literal["dry_run", "start", "pause", "resume", "stop", "dock", "test_start_stop"]
    request_id: str = Field(min_length=8, max_length=100)
    actor: str = Field(default="Fibaro10", min_length=1, max_length=100)
    confirmation: str = Field(min_length=1, max_length=200)
    test_duration_seconds: int = Field(default=5, ge=3, le=12)


TELEMETRY_SETTING_COMMANDS = (
    "GET_CONSUMABLE",
    "GET_CLEAN_SUMMARY",
    "GET_SOUND_VOLUME",
    "GET_DND_TIMER",
    "GET_CHILD_LOCK_STATUS",
    "GET_LED_STATUS",
    "GET_FLOW_LED_STATUS",
    "GET_DUST_COLLECTION_MODE",
    "GET_DUST_COLLECTION_SWITCH_STATUS",
    "GET_SMART_WASH_PARAMS",
    "GET_WASH_TOWEL_MODE",
    "GET_WASH_TOWEL_PARAMS",
    "GET_WASH_WATER_TEMPERATURE",
    "GET_AUTO_DELIVERY_CLEANING_FLUID",
    "APP_GET_DRYER_SETTING",
    "GET_MOP_MOTOR_STATUS",
    "GET_WATER_BOX_CUSTOM_MODE",
    "GET_HANDLE_LEAK_WATER_STATUS",
    "GET_ROOM_MAPPING",
    "GET_TIMEZONE",
    "GET_TIMER",
    "GET_SERVER_TIMER",
    "GET_TIMER_SUMMARY",
    "GET_SERIAL_NUMBER",
    "GET_CARPET_MODE",
    "GET_CUSTOM_MODE",
    "GET_DOCK_INFO",
    "GET_MAP_STATUS",
    "GET_PERSIST",
    "GET_VALLEY_ELECTRICITY_TIMER",
)

WASH_FILL_DOCK_TYPES = {3, 6, 7, 8, 9, 10, 14, 15, 16, 17, 18, 22, 27}


def is_unsupported_command_error(error: str) -> bool:
    message = error.lower()
    return any(marker in message for marker in ("not recognized", "unknown method", "not supported", "unsupported"))


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


def local_now() -> dt.datetime:
    return dt.datetime.now(LOCAL_TZ).replace(microsecond=0)


def local_now_iso() -> str:
    return local_now().isoformat()


def local_now_naive_iso() -> str:
    return local_now().replace(tzinfo=None).isoformat()


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dt.datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return jsonable(value.model_dump())
    if hasattr(value, "dict"):
        return jsonable(value.dict())
    if hasattr(value, "__dict__"):
        return jsonable({key: item for key, item in vars(value).items() if not key.startswith("_")})
    return str(value)


def first_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return next((item for item in value if isinstance(item, dict)), {})
    return {}


def enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def enum_name(value: Any) -> str | None:
    return getattr(value, "name", None) if value is not None else None


def status_telemetry(status: dict[str, Any], model: str | None) -> dict[str, Any]:
    """Normalize dynamic status while retaining the complete vendor payload."""
    from roborock.data.v1.v1_containers import ModelStatus, Status

    status_class = ModelStatus.get(model or "", Status)
    typed = status_class.from_dict(status)
    dock_type = enum_value(getattr(typed, "dock_type", None))
    supports_water_tanks = dock_type in WASH_FILL_DOCK_TYPES

    def typed_status(name: str, *, supported: bool = True) -> tuple[Any, str | None]:
        if not supported:
            return None, None
        try:
            value = getattr(typed, name, None)
        except (TypeError, ValueError):
            return None, None
        return enum_value(value), enum_name(value)

    clear_water_code, clear_water_name = typed_status("clear_water_box_status", supported=supports_water_tanks)
    dirty_water_code, dirty_water_name = typed_status("dirty_water_box_status", supported=supports_water_tanks)
    dust_bag_code, dust_bag_name = typed_status("dust_bag_status", supported=bool(dock_type))
    clean_fluid_code, clean_fluid_name = typed_status("clean_fluid_status", supported=supports_water_tanks)
    state = getattr(typed, "state", None)
    charge_status = getattr(typed, "charge_status", None)
    dock_error = getattr(typed, "dock_error_status", None)

    return {
        "state_code": enum_value(state),
        "state_name": enum_name(state),
        "battery": getattr(typed, "battery", None),
        "error_code": enum_value(getattr(typed, "error_code", None)),
        "in_cleaning": enum_value(getattr(typed, "in_cleaning", None)),
        "in_returning": getattr(typed, "in_returning", None),
        "clean_time_seconds": getattr(typed, "clean_time", None),
        "clean_area_raw": getattr(typed, "clean_area", None),
        "clean_percent": getattr(typed, "clean_percent", None),
        "fan_power": enum_value(getattr(typed, "fan_power", None)),
        "water_box_mode": enum_value(getattr(typed, "water_box_mode", None)),
        "mop_mode": enum_value(getattr(typed, "mop_mode", None)),
        "charge_status": enum_value(charge_status),
        "charge_status_name": enum_name(charge_status),
        "is_charging": enum_value(state) == 8,
        "dock_type": dock_type,
        "dock_type_name": enum_name(getattr(typed, "dock_type", None)),
        "dock_error_status": enum_value(dock_error),
        "dock_error_name": enum_name(dock_error),
        "dust_collection_status": getattr(typed, "dust_collection_status", None),
        "auto_dust_collection": getattr(typed, "auto_dust_collection", None),
        "wash_status": getattr(typed, "wash_status", None),
        "wash_phase": getattr(typed, "wash_phase", None),
        "wash_ready": getattr(typed, "wash_ready", None),
        "dry_status": getattr(typed, "dry_status", None),
        "water_shortage_status": getattr(typed, "water_shortage_status", None),
        "water_box_status": getattr(typed, "water_box_status", None),
        "water_box_carriage_status": getattr(typed, "water_box_carriage_status", None),
        "clear_water_status": clear_water_code,
        "clear_water_status_name": clear_water_name,
        "dirty_water_status": dirty_water_code,
        "dirty_water_status_name": dirty_water_name,
        "dust_bag_status": dust_bag_code,
        "dust_bag_status_name": dust_bag_name,
        "clean_fluid_status": clean_fluid_code,
        "clean_fluid_status_name": clean_fluid_name,
        "water_box_filter_status": (
            getattr(typed, "water_box_filter_status", None) if supports_water_tanks else None
        ),
        "dock_cool_fan_status": getattr(typed, "dock_cool_fan_status", None),
        "dss": getattr(typed, "dss", None),
        "rss": getattr(typed, "rss", None),
        "status_raw": status,
    }


def load_state() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    defaults = {"robots": {}, "last_sync": None, "last_error": None, "pending_batches": 0}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            state = {}
        if not isinstance(state, dict):
            state = {}
        for key, value in defaults.items():
            state.setdefault(key, value)
        return state
    return defaults.copy()


def save_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_device_identifier(email: str) -> str:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    client_ids = json.loads(CLIENT_IDS_FILE.read_text(encoding="utf-8")) if CLIENT_IDS_FILE.exists() else {}
    if email not in client_ids:
        client_ids[email] = secrets.token_urlsafe(16)
        CLIENT_IDS_FILE.write_text(json.dumps(client_ids, indent=2), encoding="utf-8")
    return str(client_ids[email])


def create_web_api(email: str) -> Any:
    from roborock.web_api import RoborockApiClient

    web_api = RoborockApiClient(username=email)
    web_api._device_identifier = get_device_identifier(email)
    return web_api


def save_user_data(user_data: Any) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with CACHE_FILE.open("wb") as file:
        pickle.dump(user_data, file)


def load_user_data() -> Any:
    if not CACHE_FILE.exists():
        raise RuntimeError("Roborock-login mangler. Send kode og logg inn i Roborock_logger først.")
    with CACHE_FILE.open("rb") as file:
        return pickle.load(file)


async def request_code(email: str) -> None:
    from roborock.web_api import PreparedRequest

    web_api = create_web_api(email)
    base_url = await web_api.base_url
    header_clientid = web_api._get_header_client_id()
    code_request = PreparedRequest(
        base_url,
        web_api.session,
        {
            "header_clientid": header_clientid,
            "Content-Type": "application/x-www-form-urlencoded",
            "header_clientlang": "en",
        },
    )
    response = await code_request.request(
        "post",
        "/api/v4/email/code/send",
        params={"email": email, "type": "login", "platform": ""},
    )
    if response is None or response.get("code") != 200:
        raise RuntimeError(f"Kunne ikke sende kode: {response}")


async def code_login(email: str, code: str) -> None:
    from roborock.web_api import PreparedRequest, UserData

    web_api = create_web_api(email)
    base_url = await web_api.base_url
    country = await web_api.country
    country_code = await web_api.country_code
    x_mercy_ks = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
    x_mercy_k = await web_api._sign_key_v3(x_mercy_ks)
    request = PreparedRequest(
        base_url,
        web_api.session,
        {
            "header_clientid": web_api._get_header_client_id(),
            "x-mercy-ks": x_mercy_ks,
            "x-mercy-k": x_mercy_k,
            "Content-Type": "application/json",
            "header_clientlang": "en",
            "header_appversion": "4.54.02",
            "header_phonesystem": "iOS",
            "header_phonemodel": "iPhone16,1",
        },
    )
    response = await request.request(
        "post",
        "/api/v4/auth/email/login/code",
        params={
            "country": country,
            "countryCode": country_code,
            "email": email,
            "code": code,
            "majorVersion": 14,
            "minorVersion": 0,
        },
    )
    if response is None or response.get("code") != 200:
        raise RuntimeError(f"Roborock-login feilet: {response}")
    save_user_data(UserData.from_dict(response["data"]))


def load_cached_home_data() -> dict[str, Any] | None:
    if not HOME_CACHE_FILE.exists():
        return None
    return json.loads(HOME_CACHE_FILE.read_text(encoding="utf-8"))


def save_home_data(home: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HOME_CACHE_FILE.write_text(json.dumps(home, ensure_ascii=False, indent=2), encoding="utf-8")


def cached_home_is_fresh() -> bool:
    if not HOME_CACHE_FILE.exists():
        return False
    age_seconds = dt.datetime.now().timestamp() - HOME_CACHE_FILE.stat().st_mtime
    return age_seconds < HOME_REFRESH_SECONDS


async def get_home_data(email: str, force_refresh: bool = False) -> dict[str, Any]:
    if not force_refresh and cached_home_is_fresh():
        cached = load_cached_home_data()
        if cached:
            cached["_cache"] = {"source": "file", "fresh": True}
            return cached
    web_api = create_web_api(email)
    try:
        home = jsonable(await web_api.get_home_data_v3(load_user_data()))
        home["_cache"] = {"source": "cloud", "fresh": True}
        save_home_data(home)
        return home
    except Exception as exc:
        cached = load_cached_home_data()
        if cached:
            cached["_cache"] = {"source": "file", "fresh": False, "error": str(exc)}
            return cached
        raise


async def get_local_rpc(device: dict[str, Any], host: str):
    from roborock.devices.rpc.v1_channel import RpcChannel, RpcStrategy, decode_rpc_response
    from roborock.devices.transport.local_channel import LocalChannel
    from roborock.roborock_message import RoborockMessageProtocol
    from roborock.util import RoborockLoggerAdapter

    channel = LocalChannel(host, device["local_key"], device["duid"])
    await channel.connect()
    logger = RoborockLoggerAdapter(duid=device["duid"], logger=logging.getLogger("roborock_logger.local"))
    strategy = RpcStrategy(
        name="local",
        channel=channel,
        encoder=lambda request: request.encode_message(
            RoborockMessageProtocol.GENERAL_REQUEST,
            version=channel.protocol_version,
        ),
        decoder=decode_rpc_response,
    )
    return RpcChannel(lambda: [strategy], logger), channel


def append_control_log(entry: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with CONTROL_LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")


def control_device(duid: str) -> tuple[dict[str, Any], str, str | None]:
    home = load_cached_home_data()
    if not home:
        raise HTTPException(status_code=503, detail="Roborock-enhetslisten er ikke synkronisert")
    device = next(
        (
            item
            for item in home.get("devices", []) + home.get("received_devices", [])
            if str(item.get("duid") or "") == duid
        ),
        None,
    )
    if not device or not device.get("local_key"):
        raise HTTPException(status_code=404, detail="Roboten finnes ikke eller mangler lokal nøkkel")
    state = load_state()
    host = str((((state.get("robots") or {}).get(duid) or {}).get("local_ip") or "")).strip()
    if not host:
        raise HTTPException(status_code=409, detail="Roboten mangler kjent lokal IP-adresse")
    products = {product.get("id"): product for product in home.get("products", [])}
    model = (products.get(device.get("product_id")) or {}).get("model")
    return device, host, model


async def read_control_status(rpc: Any, model: str | None) -> dict[str, Any]:
    from roborock.roborock_typing import RoborockCommand

    raw = first_dict(jsonable(await asyncio.wait_for(rpc.send_command(RoborockCommand.GET_STATUS), timeout=5)))
    normalized = status_telemetry(raw, model)
    return {
        "state_code": normalized.get("state_code"),
        "state_name": normalized.get("state_name"),
        "battery": normalized.get("battery"),
        "error_code": normalized.get("error_code"),
        "in_cleaning": normalized.get("in_cleaning"),
        "in_returning": normalized.get("in_returning"),
        "charge_status": normalized.get("charge_status"),
    }


def control_state_name(snapshot: dict[str, Any]) -> str:
    return str(snapshot.get("state_name") or "").strip().lower()


def control_is_active(snapshot: dict[str, Any]) -> bool:
    state_name = control_state_name(snapshot)
    return state_name in {
        "cleaning",
        "segment_cleaning",
        "zone_cleaning",
        "spot_cleaning",
        "going_to_target",
        "mapping",
    }


async def wait_for_control_state(
    rpc: Any,
    model: str | None,
    predicate: Any,
    *,
    timeout_seconds: float = 8,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        await asyncio.sleep(0.75)
        latest = await read_control_status(rpc, model)
        if predicate(latest):
            return latest
    return latest


def validate_control_start(snapshot: dict[str, Any]) -> None:
    if control_is_active(snapshot):
        raise HTTPException(status_code=409, detail="Roboten rengjør allerede")
    error_code = snapshot.get("error_code")
    if error_code not in (None, 0, "0"):
        raise HTTPException(status_code=409, detail=f"Roboten har aktiv feil {error_code}")
    battery = snapshot.get("battery")
    if battery is not None and int(battery) < 30:
        raise HTTPException(status_code=409, detail=f"Batteriet er for lavt for kontrolltest ({battery} %)")


async def execute_control_command(duid: str, values: ControlRequest) -> dict[str, Any]:
    from roborock.roborock_typing import RoborockCommand

    expected_confirmation = f"CONFIRM:{duid}:{values.action}"
    if not secrets.compare_digest(values.confirmation, expected_confirmation):
        raise HTTPException(status_code=400, detail="Ugyldig kontrollbekreftelse")
    device, host, model = control_device(duid)
    started_at = local_now_iso()
    audit: dict[str, Any] = {
        "request_id": values.request_id,
        "duid": duid,
        "robot_name": device.get("name"),
        "action": values.action,
        "actor": values.actor,
        "started_at": started_at,
        "status": "running",
    }
    rpc = channel = None
    try:
        rpc, channel = await get_local_rpc(device, host)
        before = await read_control_status(rpc, model)
        audit["before"] = before
        result: Any = None

        if values.action == "dry_run":
            result = {"validated": True, "host": host, "model": model}
            after = before
        elif values.action in {"start", "resume"}:
            if values.action == "start":
                validate_control_start(before)
            result = jsonable(await rpc.send_command(RoborockCommand.APP_START))
            after = await wait_for_control_state(rpc, model, control_is_active)
        elif values.action == "pause":
            result = jsonable(await rpc.send_command(RoborockCommand.APP_PAUSE))
            after = await wait_for_control_state(
                rpc,
                model,
                lambda snapshot: control_state_name(snapshot) == "paused" or not control_is_active(snapshot),
            )
        elif values.action in {"stop", "dock"}:
            if values.action == "stop" and control_is_active(before):
                await rpc.send_command(RoborockCommand.APP_PAUSE)
                await asyncio.sleep(1)
            result = jsonable(await rpc.send_command(RoborockCommand.APP_CHARGE))
            after = await wait_for_control_state(
                rpc,
                model,
                lambda snapshot: control_state_name(snapshot)
                in {"returning", "returning_home", "charging", "charging_complete", "idle"},
            )
        else:
            validate_control_start(before)
            await rpc.send_command(RoborockCommand.APP_START)
            active = await wait_for_control_state(rpc, model, control_is_active)
            if not control_is_active(active):
                raise RuntimeError("Roboten bekreftet ikke at rengjøringen startet")
            await asyncio.sleep(values.test_duration_seconds)
            await rpc.send_command(RoborockCommand.APP_PAUSE)
            await wait_for_control_state(
                rpc,
                model,
                lambda snapshot: control_state_name(snapshot) == "paused" or not control_is_active(snapshot),
                timeout_seconds=5,
            )
            result = jsonable(await rpc.send_command(RoborockCommand.APP_CHARGE))
            after = await wait_for_control_state(
                rpc,
                model,
                lambda snapshot: control_state_name(snapshot)
                in {"returning", "returning_home", "charging", "charging_complete", "idle"},
            )

        audit.update(
            {
                "status": "ok",
                "finished_at": local_now_iso(),
                "after": after,
                "result": result,
            }
        )
        append_control_log(audit)
        return audit
    except HTTPException as exc:
        audit.update({"status": "rejected", "finished_at": local_now_iso(), "error": str(exc.detail)})
        append_control_log(audit)
        raise
    except Exception as exc:
        audit.update(
            {
                "status": "error",
                "finished_at": local_now_iso(),
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        append_control_log(audit)
        raise HTTPException(status_code=502, detail=f"Roborock-kommandoen feilet: {exc}") from exc
    finally:
        if channel is not None:
            channel.close()


async def scan_hosts(subnet: str = ROBOROCK_SUBNET) -> list[str]:
    async def check(host: str) -> str | None:
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(host, ROBOROCK_LOCAL_PORT), timeout=0.35)
            writer.close()
            await writer.wait_closed()
            return host
        except Exception:
            return None

    hosts = [f"{subnet}{index}" for index in range(1, 255)]
    return [host for host in await asyncio.gather(*(check(host) for host in hosts)) if host]


async def find_local_host(device: dict[str, Any], candidates: list[str]) -> tuple[str | None, dict[str, Any], list[dict[str, Any]]]:
    from roborock.roborock_typing import RoborockCommand

    probes = []
    for host in candidates:
        try:
            rpc, channel = await get_local_rpc(device, host)
            try:
                network = await rpc.send_command(RoborockCommand.GET_NETWORK_INFO)
            finally:
                channel.close()
            return host, jsonable(network), probes
        except Exception as exc:
            probes.append({"source": "local", "command": f"connect {host}", "ok": False, "error": str(exc)})
    return None, {}, probes


async def local_robot_data(device: dict[str, Any], host: str, history_limit: int) -> dict[str, Any]:
    from roborock.roborock_typing import RoborockCommand

    rpc, channel = await get_local_rpc(device, host)
    try:
        status = jsonable(await rpc.send_command(RoborockCommand.GET_STATUS))
        consumables = jsonable(await rpc.send_command(RoborockCommand.GET_CONSUMABLE))
        clean_summary = jsonable(await rpc.send_command(RoborockCommand.GET_CLEAN_SUMMARY))
        records = clean_summary.get("records", []) if isinstance(clean_summary, dict) else []
        clean_jobs = []
        for record_id in records[:history_limit]:
            raw_record = jsonable(await rpc.send_command(RoborockCommand.GET_CLEAN_RECORD, params=[record_id]))
            items = raw_record if isinstance(raw_record, list) else [raw_record]
            for item in items:
                if isinstance(item, dict):
                    item["id"] = record_id
                    if item.get("duration") is not None:
                        item["duration_minutes"] = round(item["duration"] / 60, 1)
                    if item.get("area") is not None:
                        item["area_m2"] = round(item["area"] / 1_000_000, 2)
                    if item.get("cleaned_area") is not None:
                        item["cleaned_area_m2"] = round(item["cleaned_area"] / 1_000_000, 2)
                    clean_jobs.append(item)
        return {
            "status": status,
            "consumables": consumables,
            "clean_summary": clean_summary,
            "clean_jobs": clean_jobs,
        }
    finally:
        channel.close()


async def map_data(email: str, duid: str) -> dict[str, Any]:
    from roborock.devices.traits.v1.map_content import MapContentTrait

    from roborock.devices.device_manager import UserParams, create_device_manager

    manager = await create_device_manager(UserParams(username=email, user_data=load_user_data()))
    try:
        device = await manager.get_device(duid)
        if not device or not device.v1_properties:
            return {}
        await device.v1_properties.start()
        trait: MapContentTrait = device.v1_properties.map_content
        await trait.refresh()
        if not trait.image_content:
            return {}
        image_size = None
        if trait.map_data and trait.map_data.image:
            image_size = list(trait.map_data.image.data.size)
        return {
            "image_base64": base64.b64encode(trait.image_content).decode("ascii"),
            "image_bytes": len(trait.image_content),
            "raw_bytes": len(trait.raw_api_response or b""),
            "image_size": image_size,
            "rooms": len(trait.map_data.rooms or []) if trait.map_data else None,
            "zones": len(trait.map_data.zones or []) if trait.map_data else None,
            "charger": trait.map_data.charger.as_dict() if trait.map_data and trait.map_data.charger else None,
            "vacuum_position": trait.map_data.vacuum_position.as_dict() if trait.map_data and trait.map_data.vacuum_position else None,
        }
    finally:
        await manager.close()


async def schedules_and_scenes(email: str, duid: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    user_data = load_user_data()
    web_api = create_web_api(email)
    schedules = jsonable(await web_api.get_schedules(user_data, duid))
    scenes = jsonable(await web_api.get_scenes(user_data, duid))
    return schedules, scenes


def post_to_fibaro10(batch: dict[str, Any], endpoint: str = "/api/renhold/ingest") -> None:
    url = f"{FIBARO10_API_BASE_URL}{endpoint}"
    body = json.dumps(batch, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Roborock_logger/1.0",
    }
    if FIBARO10_API_USERNAME and FIBARO10_API_PASSWORD:
        headers["x-access-username"] = FIBARO10_API_USERNAME
        headers["x-access-password"] = FIBARO10_API_PASSWORD
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status >= 300:
            raise RuntimeError(f"Fibaro10 svarte {response.status}")


def post_import_status(ok: bool, message: str, robots_count: int | None = None, raw: dict[str, Any] | None = None) -> None:
    payload = {
        "job_name": "roborock_sync",
        "title": "Roborock logger",
        "category": "Renhold",
        "source": "Roborock_logger",
        "ok": ok,
        "records_imported": robots_count,
        "records_total": robots_count,
        "message": message,
        "raw": {"collector_id": COLLECTOR_ID, **(raw or {})},
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Roborock_logger/1.0",
    }
    if FIBARO10_API_USERNAME and FIBARO10_API_PASSWORD:
        headers["x-access-username"] = FIBARO10_API_USERNAME
        headers["x-access-password"] = FIBARO10_API_PASSWORD
    request = urllib.request.Request(
        f"{FIBARO10_API_BASE_URL}/api/import-status/report",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=12):
            pass
    except Exception:
        pass


def queue_batch(batch: dict[str, Any], endpoint: str = "/api/renhold/ingest") -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with QUEUE_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps({"endpoint": endpoint, "payload": batch}, ensure_ascii=False) + "\n")


def resend_queue() -> int:
    if not QUEUE_FILE.exists():
        return 0
    lines = QUEUE_FILE.read_text(encoding="utf-8").splitlines()
    remaining = []
    sent = 0
    for line in lines:
        if not line.strip():
            continue
        queued = json.loads(line)
        if isinstance(queued, dict) and isinstance(queued.get("payload"), dict):
            endpoint = str(queued.get("endpoint") or "/api/renhold/ingest")
            batch = queued["payload"]
        else:
            endpoint = "/api/renhold/ingest"
            batch = queued
        try:
            post_to_fibaro10(batch, endpoint)
            sent += 1
        except Exception:
            remaining.append(line)
    QUEUE_FILE.write_text("\n".join(remaining) + ("\n" if remaining else ""), encoding="utf-8")
    return sent


async def local_telemetry_data(
    device: dict[str, Any],
    host: str,
    model: str | None,
    *,
    include_settings: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from roborock.roborock_typing import RoborockCommand

    rpc, channel = await get_local_rpc(device, host)
    probes: list[dict[str, Any]] = []

    async def read_command(name: str, timeout: float = 3.0) -> tuple[bool, Any]:
        command = getattr(RoborockCommand, name, None)
        if command is None:
            error = "Kommandoen finnes ikke i installert python-roborock"
            probes.append(
                {"source": "local-telemetry", "command": name, "ok": False, "error": error, "result_type": "missing"}
            )
            return False, None
        try:
            result = await asyncio.wait_for(rpc.send_command(command), timeout=timeout)
            value = jsonable(result)
            probes.append(
                {
                    "source": "local-telemetry",
                    "command": name,
                    "ok": True,
                    "result_type": type(result).__name__,
                    "value": value,
                }
            )
            return True, value
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            probes.append(
                {
                    "source": "local-telemetry",
                    "command": name,
                    "ok": False,
                    "error": error,
                    "result_type": type(exc).__name__,
                }
            )
            if is_unsupported_command_error(error):
                telemetry_unsupported_commands.setdefault(str(device.get("duid") or ""), set()).add(name)
            return False, None

    try:
        status_ok, status_result = await read_command("GET_STATUS", timeout=5.0)
        if not status_ok:
            raise RuntimeError(probes[-1].get("error") or "GET_STATUS feilet")
        network_ok, network_result = await read_command("GET_NETWORK_INFO")
        status = first_dict(status_result)
        telemetry = status_telemetry(status, model)
        network = first_dict(network_result) if network_ok else {}
        telemetry.update(
            {
                "local_ip": network.get("ip") or host,
                "rssi": network.get("rssi"),
                "network_raw": network,
            }
        )

        if include_settings:
            unsupported = telemetry_unsupported_commands.setdefault(str(device.get("duid") or ""), set())
            for name in TELEMETRY_SETTING_COMMANDS:
                if name not in unsupported:
                    await read_command(name)
        return telemetry, probes
    finally:
        channel.close()


async def collect_telemetry_once(force_settings: bool = False) -> dict[str, Any]:
    home = load_cached_home_data()
    if not home:
        home = await get_home_data(ROBOROCK_EMAIL, force_refresh=False)
    devices = home.get("devices", []) + home.get("received_devices", [])
    products = {product.get("id"): product for product in home.get("products", [])}
    state = load_state()
    robots = []
    now_monotonic = time.monotonic()

    for device in devices:
        duid = str(device.get("duid") or "")
        if not duid:
            continue
        previous_robot = ((state.get("robots") or {}).get(duid) or {})
        host = previous_robot.get("local_ip")
        product = products.get(device.get("product_id"), {})
        model = product.get("model")
        include_settings = force_settings or (
            now_monotonic - telemetry_last_settings_at.get(duid, 0) >= TELEMETRY_SETTINGS_INTERVAL_SECONDS
        )
        item: dict[str, Any] = {
            "duid": duid,
            "name": device.get("name"),
            "model": model,
            "local_ip": host,
            "ok": False,
            "settings_refreshed": include_settings,
        }
        if not host:
            item["error"] = "Lokal IP mangler; venter på ordinær Roborock-synk"
            robots.append(item)
            continue
        try:
            telemetry, probes = await local_telemetry_data(
                device,
                host,
                model,
                include_settings=include_settings,
            )
            item.update({"ok": True, "telemetry": telemetry, "probes": probes})
            if include_settings:
                telemetry_last_settings_at[duid] = now_monotonic
            state.setdefault("robots", {}).setdefault(duid, {})["last_telemetry"] = local_now_iso()
            state["robots"][duid]["last_telemetry_error"] = None
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
            state.setdefault("robots", {}).setdefault(duid, {})["last_telemetry_error"] = item["error"]
        robots.append(item)

    batch = {
        "source": "Roborock_logger telemetry",
        "collector_id": COLLECTOR_ID,
        "timestamp": local_now_naive_iso(),
        "ok": all(robot.get("ok") for robot in robots) if robots else False,
        "robots": robots,
        "extra": {
            "interval_seconds": TELEMETRY_INTERVAL_SECONDS,
            "settings_interval_seconds": TELEMETRY_SETTINGS_INTERVAL_SECONDS,
        },
    }
    try:
        resend_queue()
        post_to_fibaro10(batch, "/api/renhold/telemetry/ingest")
        state["last_telemetry"] = local_now_iso()
        state["last_telemetry_error"] = None
    except Exception as exc:
        queue_batch(batch, "/api/renhold/telemetry/ingest")
        state["last_telemetry_error"] = str(exc)
    state["pending_batches"] = sum(1 for _ in QUEUE_FILE.open(encoding="utf-8")) if QUEUE_FILE.exists() else 0
    save_state(state)
    return batch


async def collect_once(include_maps: bool = False, force_home_refresh: bool = False) -> dict[str, Any]:
    home = await get_home_data(ROBOROCK_EMAIL, force_refresh=force_home_refresh)
    devices = home.get("devices", []) + home.get("received_devices", [])
    products = {product.get("id"): product for product in home.get("products", [])}
    state = load_state()
    known_hosts = [
        robot.get("local_ip")
        for robot in (state.get("robots") or {}).values()
        if robot.get("local_ip")
    ]
    scanned_hosts = await scan_hosts()
    candidates = list(dict.fromkeys(known_hosts + scanned_hosts))
    robots = []
    for device in devices:
        duid = device.get("duid")
        if not duid:
            continue
        previous_robot = ((state.get("robots") or {}).get(duid) or {})
        product = products.get(device.get("product_id"), {})
        robot = {
            "duid": duid,
            "name": device.get("name"),
            "product": product.get("name"),
            "model": product.get("model"),
            "firmware": device.get("fv"),
            "protocol_version": device.get("pv"),
            "online": device.get("online"),
            "shared": bool(device.get("share")),
            "time_zone_id": device.get("time_zone_id"),
            "cloud": {"status_raw": device.get("device_status")},
            "metadata": {key: value for key, value in device.items() if key != "local_key"},
        }
        robot_errors = []
        try:
            schedules, scenes = await schedules_and_scenes(ROBOROCK_EMAIL, duid)
            robot["schedules"] = schedules
            robot["scenes"] = scenes
        except Exception as exc:
            robot_errors.append(f"cloud schedules: {exc}")
            robot["probe_results"] = [{"source": "cloud", "command": "schedules_and_scenes", "ok": False, "error": str(exc)}]
        host = None
        if device.get("local_key"):
            try:
                preferred_host = previous_robot.get("local_ip")
                device_candidates = list(dict.fromkeys(([preferred_host] if preferred_host else []) + candidates))
                host, network, probes = await find_local_host(device, device_candidates)
                robot.setdefault("probe_results", []).extend(probes)
                if host:
                    robot["local_ip"] = host
                    robot["network"] = network
                    robot.update(await local_robot_data(device, host, HISTORY_LIMIT))
            except Exception as exc:
                robot_errors.append(f"local: {exc}")
                robot.setdefault("probe_results", []).append({"source": "local", "command": "local_sync", "ok": False, "error": str(exc)})
        else:
            robot_errors.append("local_key mangler")
        if not robot.get("local_ip") and previous_robot.get("local_ip"):
            robot["local_ip"] = previous_robot.get("local_ip")
        if include_maps:
            try:
                robot["map"] = await map_data(ROBOROCK_EMAIL, duid)
            except Exception as exc:
                robot_errors.append(f"map: {exc}")
                robot.setdefault("probe_results", []).append({"source": "cloud-map", "command": "get_map_v1", "ok": False, "error": str(exc)})
        if robot_errors:
            robot["last_error"] = " | ".join(robot_errors)
        robots.append(robot)
        state["robots"][duid] = {
            "name": robot.get("name"),
            "model": robot.get("model"),
            "local_ip": robot.get("local_ip"),
            "last_status": local_now_iso(),
            "online": robot.get("online"),
            "last_error": robot.get("last_error"),
        }
    batch = {
        "source": "Roborock_logger",
        "collector_id": COLLECTOR_ID,
        "timestamp": local_now_naive_iso(),
        "ok": True,
        "robots": robots,
        "extra": {"home_id": home.get("id"), "host_candidates": candidates, "home_cache": home.get("_cache")},
    }
    try:
        resend_queue()
        post_to_fibaro10(batch)
        state["last_sync"] = local_now_iso()
        state["last_error"] = None
        post_import_status(True, f"{len(robots)} roboter synkronisert", len(robots), {"home_cache": home.get("_cache")})
    except Exception as exc:
        queue_batch(batch)
        state["last_error"] = str(exc)
        post_import_status(False, f"Kunne ikke sende Roborock-data: {exc}", len(robots), {"queued": True})
    state["pending_batches"] = sum(1 for _ in QUEUE_FILE.open(encoding="utf-8")) if QUEUE_FILE.exists() else 0
    save_state(state)
    return batch


async def sync_loop() -> None:
    while True:
        try:
            if AUTO_SYNC_ENABLED and CACHE_FILE.exists():
                async with sync_lock:
                    await collect_once(include_maps=False)
        except Exception as exc:
            state = load_state()
            state["last_error"] = str(exc)
            save_state(state)
            post_import_status(False, f"Roborock sync feilet før ingest: {exc}")
        await asyncio.sleep(max(60, STATUS_INTERVAL_SECONDS))


async def telemetry_loop() -> None:
    while True:
        try:
            if AUTO_SYNC_ENABLED and CACHE_FILE.exists():
                async with sync_lock:
                    await collect_telemetry_once()
        except Exception as exc:
            state = load_state()
            state["last_telemetry_error"] = str(exc)
            save_state(state)
        await asyncio.sleep(max(30, TELEMETRY_INTERVAL_SECONDS))


def page(content: str) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="no"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Roborock_logger</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#f5f7fb;color:#26323f}}
main{{width:min(100% - 1.4rem,980px);margin:0 auto;padding:1rem 0 2rem}}
.panel{{background:white;border:1px solid #dbe3ec;border-radius:10px;padding:1rem;margin:.8rem 0;box-shadow:0 1px 3px #0001}}
.grid{{display:grid;gap:.65rem}}@media(min-width:760px){{.grid{{grid-template-columns:repeat(3,1fr)}}}}
.metric{{background:#f9fbfe;border:1px solid #edf1f6;border-radius:8px;padding:.7rem}}.metric span{{display:block;color:#64748b;font-size:.82rem}}
.button,button{{display:inline-flex;border:1px solid #acd8e1;background:#e7f5f8;color:#176579;border-radius:7px;padding:.55rem .8rem;text-decoration:none;font-weight:700;cursor:pointer}}
input{{padding:.55rem;border:1px solid #dbe3ec;border-radius:7px}}form{{display:flex;gap:.5rem;flex-wrap:wrap}}code{{overflow-wrap:anywhere}}
</style></head><body><main><h1>Roborock_logger</h1>{content}</main></body></html>"""
    )


@app.on_event("startup")
async def startup() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    asyncio.create_task(sync_loop())
    asyncio.create_task(telemetry_loop())


@app.get("/", response_class=HTMLResponse)
async def index():
    state = load_state()
    robots = state.get("robots", {})
    robot_cards = "".join(
        f"<div class='metric'><span>{html.escape(str(robot.get('model') or ''))}</span><strong>{html.escape(str(robot.get('name') or duid))}</strong><br>"
        f"<span>IP: {robot.get('local_ip') or '-'} · online: {robot.get('online')}</span></div>"
        for duid, robot in robots.items()
    )
    login_state = "OK" if CACHE_FILE.exists() else "Mangler"
    return page(
        f"""
<section class="panel"><div class="grid">
<div class="metric"><span>Roborock-login</span><strong>{login_state}</strong></div>
<div class="metric"><span>Sist sendt</span><strong>{state.get('last_sync') or '-'}</strong></div>
<div class="metric"><span>Sist telemetri</span><strong>{state.get('last_telemetry') or '-'}</strong></div>
<div class="metric"><span>Kø</span><strong>{state.get('pending_batches', 0)}</strong></div>
</div><p>Siste feil: <code>{state.get('last_error') or state.get('last_telemetry_error') or '-'}</code></p></section>
<section class="panel"><h2>Handlinger</h2>
<p><a class="button" href="/sync-now">Synk nå</a> <a class="button" href="/telemetry-now">Telemetri nå</a> <a class="button" href="/sync-now?refresh=true">Finn nye roboter</a> <a class="button" href="/sync-now?maps=true">Synk med kart</a> <a class="button" href="/api/status">JSON status</a></p>
<h3>Login</h3>
<form action="/auth/request-code"><input name="email" value="{ROBOROCK_EMAIL}"><button>Send kode</button></form>
<form action="/auth/login"><input name="email" value="{ROBOROCK_EMAIL}"><input name="code" placeholder="Kode fra e-post"><button>Lagre login</button></form>
</section>
<section class="panel"><h2>Roboter</h2><div class="grid">{robot_cards or '<p>Ingen roboter lest ennå.</p>'}</div></section>
"""
    )


@app.get("/auth/request-code")
async def request_code_route(email: str = Query(default=ROBOROCK_EMAIL)):
    await request_code(email)
    return RedirectResponse("/", status_code=303)


@app.get("/auth/login")
async def login_route(email: str = Query(default=ROBOROCK_EMAIL), code: str = Query(...)):
    await code_login(email, code)
    return RedirectResponse("/", status_code=303)


@app.get("/sync-now")
async def sync_now(maps: bool = False, refresh: bool = False):
    try:
        async with sync_lock:
            batch = await collect_once(include_maps=maps, force_home_refresh=refresh)
        return JSONResponse(
            {
                "status": "ok",
                "robots": len(batch.get("robots", [])),
                "home_cache": (batch.get("extra") or {}).get("home_cache"),
            }
        )
    except Exception as exc:
        state = load_state()
        state["last_error"] = f"manual sync: {exc}"
        save_state(state)
        post_import_status(False, f"Manuell Roborock sync feilet: {exc}")
        return JSONResponse(
            {"status": "error", "error": str(exc)},
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@app.get("/api/status")
async def status():
    return load_state()


@app.post("/api/control/{duid}")
async def control_robot(
    duid: str,
    values: ControlRequest,
    x_roborock_control_token: str | None = Header(default=None),
):
    if not ROBOROCK_CONTROL_TOKEN:
        raise HTTPException(status_code=503, detail="Robotstyring er ikke aktivert")
    if not x_roborock_control_token or not secrets.compare_digest(
        x_roborock_control_token,
        ROBOROCK_CONTROL_TOKEN,
    ):
        raise HTTPException(status_code=401, detail="Ugyldig kontrolltoken")
    async with sync_lock:
        return await execute_control_command(duid, values)


@app.get("/telemetry-now")
async def telemetry_now(settings: bool = True):
    try:
        async with sync_lock:
            batch = await collect_telemetry_once(force_settings=settings)
        return JSONResponse(
            {
                "status": "ok" if batch.get("ok") else "partial",
                "robots": len(batch.get("robots", [])),
                "settings_refreshed": settings,
            }
        )
    except Exception as exc:
        state = load_state()
        state["last_telemetry_error"] = f"manual telemetry: {exc}"
        save_state(state)
        return JSONResponse(
            {"status": "error", "error": str(exc)},
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@app.get("/status")
async def status_alias():
    return load_state()


@app.get("/health")
async def health():
    state = load_state()
    return {
        "ok": not bool(state.get("last_error") or state.get("last_telemetry_error")),
        "last_sync": state.get("last_sync"),
        "last_telemetry": state.get("last_telemetry"),
        "timezone": LOCAL_TIMEZONE,
        "pending_batches": state.get("pending_batches", 0),
        "robots": len(state.get("robots") or {}),
        "control_enabled": bool(ROBOROCK_CONTROL_TOKEN),
    }


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
