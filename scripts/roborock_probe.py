import argparse
import asyncio
import datetime as dt
import getpass
import json
import logging
import os
import pickle
import secrets
import string
import sys
from pathlib import Path
from typing import Any


CACHE_DIR = Path.home() / ".fibaro10"
CACHE_FILE = CACHE_DIR / "roborock_user_data.pickle"
CLIENT_IDS_FILE = CACHE_DIR / "roborock_client_ids.json"
SECRET_KEYS = {"token", "u", "s", "h", "k", "r", "rruid", "uid", "local_key"}
DEFAULT_ROBOROCK_HOST = "192.168.2.91"
LOCAL_READ_COMMANDS = (
    ("status", "GET_STATUS", None),
    ("consumable", "GET_CONSUMABLE", None),
    ("clean_summary", "GET_CLEAN_SUMMARY", None),
    ("network_info", "GET_NETWORK_INFO", None),
    ("sound_volume", "GET_SOUND_VOLUME", None),
    ("dnd_timer", "GET_DND_TIMER", None),
    ("child_lock", "GET_CHILD_LOCK_STATUS", None),
    ("led_status", "GET_LED_STATUS", None),
    ("flow_led_status", "GET_FLOW_LED_STATUS", None),
    ("dust_collection_mode", "GET_DUST_COLLECTION_MODE", None),
    ("smart_wash_params", "GET_SMART_WASH_PARAMS", None),
    ("wash_towel_mode", "GET_WASH_TOWEL_MODE", None),
    ("room_mapping", "GET_ROOM_MAPPING", None),
    ("timezone", "GET_TIMEZONE", None),
    ("timer", "GET_TIMER", None),
    ("server_timer", "GET_SERVER_TIMER", None),
    ("timer_summary", "GET_TIMER_SUMMARY", None),
    ("serial_number", "GET_SERIAL_NUMBER", None),
    ("carpet_mode", "GET_CARPET_MODE", None),
    ("custom_mode", "GET_CUSTOM_MODE", None),
    ("water_box_custom_mode", "GET_WATER_BOX_CUSTOM_MODE", None),
    ("dock_info", "GET_DOCK_INFO", None),
    ("map_status", "GET_MAP_STATUS", None),
    ("persist_map", "GET_PERSIST", None),
)


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
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


def print_json(value: Any) -> None:
    text = json.dumps(jsonable(value), indent=2, ensure_ascii=False, default=str)
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")


def redacted(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if str(key).lower() in SECRET_KEYS and item is not None:
                result[str(key)] = "***"
            else:
                result[str(key)] = redacted(item)
        return result
    if isinstance(value, list):
        return [redacted(item) for item in value]
    return value


def save_user_data(user_data: Any) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with CACHE_FILE.open("wb") as file:
        pickle.dump(user_data, file)


def load_user_data() -> Any:
    if not CACHE_FILE.exists():
        raise SystemExit(
            "Mangler lagret Roborock-login. Kjør først:\n"
            "  python scripts/roborock_probe.py request-code --email DIN_EPOST\n"
            "  python scripts/roborock_probe.py login --email DIN_EPOST --code KODE"
        )
    with CACHE_FILE.open("rb") as file:
        return pickle.load(file)


def get_device_identifier(email: str) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if CLIENT_IDS_FILE.exists():
        client_ids = json.loads(CLIENT_IDS_FILE.read_text(encoding="utf-8"))
    else:
        client_ids = {}
    if email not in client_ids:
        client_ids[email] = secrets.token_urlsafe(16)
        CLIENT_IDS_FILE.write_text(json.dumps(client_ids, indent=2), encoding="utf-8")
    return str(client_ids[email])


def create_web_api(email: str) -> Any:
    from roborock.web_api import RoborockApiClient

    web_api = RoborockApiClient(username=email)
    # Roborock appears to bind emailed login codes to header_clientid. Persisting
    # the random identifier keeps request-code and login compatible across runs.
    web_api._device_identifier = get_device_identifier(email)
    return web_api


def enum_name(enum_class: Any, value: Any) -> str | None:
    if value is None:
        return None
    try:
        return enum_class(value).name
    except ValueError:
        return None


def local_datetime(timestamp: int | None) -> str | None:
    if timestamp is None:
        return None
    return dt.datetime.fromtimestamp(timestamp).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def seconds_to_minutes(seconds: int | None) -> float | None:
    if seconds is None:
        return None
    return round(seconds / 60, 1)


def area_to_square_meters(area: int | None) -> float | None:
    if area is None:
        return None
    return round(area / 1_000_000, 2)


def find_user_data(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SystemExit("Importfilen må være JSON med objekt på toppnivå.")
    if "token" in payload and "rriot" in payload:
        return payload
    if isinstance(payload.get("user_data"), dict):
        return payload["user_data"]
    if isinstance(payload.get("userdata"), dict):
        return payload["userdata"]

    entries = payload.get("data", {}).get("entries", [])
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("domain") != "roborock":
                continue
            data = entry.get("data", {})
            if isinstance(data, dict):
                for key in ("user_data", "userdata"):
                    if isinstance(data.get(key), dict):
                        return data[key]

    raise SystemExit(
        "Fant ikke Roborock user_data. Støtter ren user_data-JSON eller Home Assistant "
        ".storage/core.config_entries med domain=roborock."
    )


def import_user_data(path: str) -> None:
    from roborock.web_api import UserData

    source = Path(path).expanduser()
    payload = json.loads(source.read_text(encoding="utf-8"))
    user_data_dict = find_user_data(payload)
    user_data = UserData.from_dict(user_data_dict)
    save_user_data(user_data)
    print(f"Roborock-login importert og lagret i {CACHE_FILE}")
    print_json(redacted(user_data_dict))


def cache_info() -> None:
    user_data = load_user_data()
    data = jsonable(user_data)
    print_json(redacted(data))


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
    code_response = await code_request.request(
        "post",
        "/api/v4/email/code/send",
        params={"email": email, "type": "login", "platform": ""},
    )
    if code_response is None or code_response.get("code") != 200:
        print_json(code_response)
        raise SystemExit("Kunne ikke sende Roborock-kode.")
    print(f"Kode er sendt til {email}.")


async def request_code_probe(email: str, legacy: bool = False) -> None:
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
    if legacy:
        code_response = await code_request.request(
            "post",
            "/api/v1/sendEmailCode",
            params={"username": email, "type": "auth"},
        )
    else:
        code_response = await code_request.request(
            "post",
            "/api/v4/email/code/send",
            params={"email": email, "type": "login", "platform": ""},
        )
    print_json(code_response)


async def request_code_legacy(email: str) -> None:
    web_api = create_web_api(email)
    await web_api.request_code()
    print(f"Gammel type kode er sendt til {email}.")


async def login(email: str, code: str) -> None:
    user_data = await dynamic_code_login(email, code)
    save_user_data(user_data)
    print(f"Login lagret i {CACHE_FILE}")
    print_json(redacted(jsonable(user_data)))


async def login_explicit(email: str, code: str, country: str, country_code: int) -> None:
    user_data = await dynamic_code_login(email, code, country=country, country_code=country_code)
    save_user_data(user_data)
    print(f"Login lagret i {CACHE_FILE}")
    print_json(redacted(jsonable(user_data)))


async def get_latest_agreement_version(web_api: Any, country: str) -> tuple[int, int]:
    from roborock.web_api import PreparedRequest

    base_url = await web_api.base_url
    agreement_request = PreparedRequest(base_url, web_api.session)
    response = await agreement_request.request(
        "get",
        "/api/v3/app/agreement/latest",
        params={"country": country},
    )
    data = response.get("data") if isinstance(response, dict) else None
    if isinstance(data, dict):
        return int(data.get("majorVersion") or 14), int(data.get("minorVersion") or 0)
    return 14, 0


async def dynamic_code_login(
    email: str,
    code: str,
    country: str | None = None,
    country_code: int | None = None,
) -> Any:
    from roborock.web_api import PreparedRequest, UserData

    web_api = create_web_api(email)
    base_url = await web_api.base_url
    if country is None:
        country = await web_api.country
    if country_code is None:
        country_code = await web_api.country_code
    if country is None or country_code is None:
        return await web_api.code_login(code)

    # openHAB's Roborock binding still uses 14/0 here even when the latest
    # agreement endpoint reports a newer version for EU accounts.
    major_version, minor_version = 14, 0
    header_clientid = web_api._get_header_client_id()
    x_mercy_ks = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
    x_mercy_k = await web_api._sign_key_v3(x_mercy_ks)
    login_request = PreparedRequest(
        base_url,
        web_api.session,
        {
            "header_clientid": header_clientid,
            "x-mercy-ks": x_mercy_ks,
            "x-mercy-k": x_mercy_k,
            "Content-Type": "application/json",
            "header_clientlang": "en",
            "header_appversion": "4.54.02",
            "header_phonesystem": "iOS",
            "header_phonemodel": "iPhone16,1",
        },
    )
    login_response = await login_request.request(
        "post",
        "/api/v4/auth/email/login/code",
        params={
            "country": country,
            "countryCode": country_code,
            "email": email,
            "code": code,
            "majorVersion": major_version,
            "minorVersion": minor_version,
        },
    )
    if login_response is None:
        raise SystemExit("Roborock returnerte ikke login-respons.")
    if login_response.get("code") != 200:
        print_json(
            {
                "agreement_version_used": {
                    "majorVersion": major_version,
                    "minorVersion": minor_version,
                    "country": country,
                    "countryCode": country_code,
                },
                "response": login_response,
            }
        )
        raise SystemExit("Roborock-login feilet. Se responsen over.")
    user_data = login_response.get("data")
    if not isinstance(user_data, dict):
        raise SystemExit("Roborock returnerte uventet brukerdata.")
    return UserData.from_dict(user_data)


async def legacy_login(email: str, code: str) -> None:
    web_api = create_web_api(email)
    user_data = await web_api.code_login(code)
    save_user_data(user_data)
    print(f"Login lagret i {CACHE_FILE}")
    print_json(redacted(jsonable(user_data)))


async def account_info(email: str) -> None:
    web_api = create_web_api(email)
    print_json(
        {
            "base_url": await web_api.base_url,
            "country": await web_api.country,
            "country_code": await web_api.country_code,
        }
    )


async def password_login(email: str, password: str | None, password_env: str | None) -> None:
    if password_env:
        password = os.getenv(password_env)
    if not password:
        password = getpass.getpass("Roborock-passord: ")
    if not password:
        raise SystemExit("Mangler passord.")

    web_api = create_web_api(email)
    user_data = await web_api.pass_login(password)
    save_user_data(user_data)
    print(f"Login lagret i {CACHE_FILE}")
    print_json(redacted(jsonable(user_data)))


async def password_probe(email: str, password: str | None, password_env: str | None) -> None:
    from roborock.web_api import PreparedRequest

    if password_env:
        password = os.getenv(password_env)
    if not password:
        password = getpass.getpass("Roborock-passord: ")
    if not password:
        raise SystemExit("Mangler passord.")

    web_api = create_web_api(email)
    base_url = await web_api.base_url
    header_clientid = web_api._get_header_client_id()
    login_request = PreparedRequest(base_url, web_api.session, {"header_clientid": header_clientid})
    login_response = await login_request.request(
        "post",
        "/api/v1/login",
        params={
            "username": email,
            "password": password,
            "needtwostepauth": "true",
        },
    )
    print_json(login_response)


async def get_device_manager(email: str):
    from roborock.devices.device_manager import UserParams, create_device_manager

    user_data = load_user_data()
    user_params = UserParams(username=email, user_data=user_data)
    return await create_device_manager(user_params)


async def get_home_data_json(email: str) -> dict[str, Any]:
    from roborock.web_api import RoborockApiClient

    user_data = load_user_data()
    web_api = RoborockApiClient(username=email)
    return jsonable(await web_api.get_home_data_v3(user_data))


async def get_rest_device(email: str, device_id: str | None) -> dict[str, Any]:
    home_data = await get_home_data_json(email)
    devices = home_data.get("devices", []) + home_data.get("received_devices", [])
    if device_id is None:
        if len(devices) != 1:
            raise SystemExit("Angi --device-id når kontoen har null eller flere enheter.")
        return devices[0]
    for device in devices:
        if device.get("duid") == device_id:
            return device
    raise SystemExit(f"Fant ikke Roborock-enhet med DUID {device_id}.")


async def show_home(email: str) -> None:
    home_data = await get_home_data_json(email)
    print_json(redacted(jsonable(home_data)))


async def list_devices(email: str) -> None:
    devices = await get_rest_devices(email)
    print_json(devices)


async def get_rest_devices(email: str) -> list[dict[str, Any]]:
    from roborock.data.v1.v1_code_mappings import RoborockStateCode

    data = await get_home_data_json(email)
    products = {product.get("id"): product for product in data.get("products", [])}
    devices = []
    for section in ("devices", "received_devices"):
        for device in data.get(section, []):
            product = products.get(device.get("product_id"), {})
            status = device.get("device_status") or {}
            state = status.get("121")
            devices.append(
                {
                    "name": device.get("name"),
                    "duid": device.get("duid"),
                    "source": section,
                    "shared": bool(device.get("share")),
                    "online": device.get("online"),
                    "firmware": device.get("fv"),
                    "protocol_version": device.get("pv"),
                    "product": product.get("name"),
                    "model": product.get("model"),
                    "battery": status.get("122"),
                    "state": state,
                    "state_name": enum_name(RoborockStateCode, state),
                    "error": status.get("120"),
                    "status_raw": status,
                }
            )
    return devices


async def list_devices_live(email: str) -> None:
    manager = await get_device_manager(email)
    devices = await manager.get_devices()
    result = []
    for device in devices:
        result.append(
            {
                "name": getattr(device, "name", None),
                "duid": getattr(device, "duid", None),
                "model": getattr(device, "model", None),
                "category": getattr(device, "category", None),
                "has_v1_properties": bool(getattr(device, "v1_properties", None)),
                "has_a01_properties": bool(getattr(device, "a01_properties", None)),
            }
        )
    print_json(result)


async def list_schedules(email: str, device_id: str | None) -> None:
    from roborock.web_api import RoborockApiClient

    user_data = load_user_data()
    if device_id is None:
        devices = await get_rest_devices(email)
        if len(devices) != 1:
            raise SystemExit("Angi --device-id når kontoen har null eller flere enheter.")
        device_id = devices[0]["duid"]

    web_api = RoborockApiClient(username=email)
    schedules = await web_api.get_schedules(user_data, device_id)
    print_json(schedules)


async def get_local_rpc(email: str, device_id: str | None, host: str):
    from roborock.devices.rpc.v1_channel import RpcChannel, RpcStrategy, decode_rpc_response
    from roborock.devices.transport.local_channel import LocalChannel
    from roborock.roborock_message import RoborockMessageProtocol
    from roborock.util import RoborockLoggerAdapter

    device = await get_rest_device(email, device_id)
    duid = device["duid"]
    channel = LocalChannel(host, device["local_key"], duid)
    await channel.connect()
    logger = RoborockLoggerAdapter(duid=duid, logger=logging.getLogger("roborock-local"))
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


async def get_local_map_rpc(email: str, device_id: str | None, host: str, request_protocol: str):
    from roborock.devices.rpc.v1_channel import RpcChannel, RpcStrategy
    from roborock.devices.transport.local_channel import LocalChannel
    from roborock.protocols.v1_protocol import create_map_response_decoder, create_security_data
    from roborock.roborock_message import RoborockMessageProtocol
    from roborock.util import RoborockLoggerAdapter

    user_data = load_user_data()
    device = await get_rest_device(email, device_id)
    duid = device["duid"]
    channel = LocalChannel(host, device["local_key"], duid)
    await channel.connect()
    security_data = create_security_data(user_data.rriot)
    logger = RoborockLoggerAdapter(duid=duid, logger=logging.getLogger("roborock-local-map"))
    protocol = (
        RoborockMessageProtocol.RPC_REQUEST
        if request_protocol == "rpc"
        else RoborockMessageProtocol.GENERAL_REQUEST
    )
    strategy = RpcStrategy(
        name=f"local-map-{request_protocol}",
        channel=channel,
        encoder=lambda request: request.encode_message(
            protocol,
            security_data=security_data,
            version=channel.protocol_version,
        ),
        decoder=create_map_response_decoder(security_data),
    )
    return RpcChannel(lambda: [strategy], logger), channel


def save_map_content(raw_map: bytes, output_file: str, raw_output_file: str | None = None) -> dict[str, Any]:
    from roborock.devices.traits.v1.map_content import MapContentConverter
    from roborock.map.map_parser import MapParser, MapParserConfig

    output = Path(output_file).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    if raw_output_file:
        raw_output = Path(raw_output_file).expanduser()
        raw_output.parent.mkdir(parents=True, exist_ok=True)
        raw_output.write_bytes(raw_map)
    else:
        raw_output = None

    content = MapContentConverter(MapParser(MapParserConfig())).parse_map_content(raw_map)
    if not content.image_content:
        raise SystemExit("Kartet ble hentet, men Roborock-parseren returnerte ikke bildeinnhold.")
    output.write_bytes(content.image_content)

    map_data = content.map_data
    image_size = None
    if map_data and map_data.image:
        image_size = list(map_data.image.data.size)
    return {
        "image_file": str(output),
        "raw_file": str(raw_output) if raw_output else None,
        "raw_bytes": len(raw_map),
        "image_bytes": len(content.image_content),
        "image_size": image_size,
        "charger": map_data.charger.as_dict() if map_data and map_data.charger else None,
        "vacuum_position": map_data.vacuum_position.as_dict() if map_data and map_data.vacuum_position else None,
        "rooms": len(map_data.rooms or []) if map_data else None,
        "zones": len(map_data.zones or []) if map_data else None,
    }


async def fetch_map_image(
    email: str,
    device_id: str | None,
    host: str,
    output_file: str,
    raw_output_file: str | None,
    method: str,
) -> None:
    from roborock.roborock_typing import RoborockCommand

    errors = []
    methods = ["local-rpc", "local-general", "cloud"] if method == "auto" else [method]
    for current_method in methods:
        try:
            if current_method == "cloud":
                manager = await get_device_manager(email)
                try:
                    if device_id is None:
                        devices = await manager.get_devices()
                        if len(devices) != 1:
                            raise SystemExit("Angi --device-id naar kontoen har null eller flere enheter.")
                        device = devices[0]
                    else:
                        device = await manager.get_device(device_id)
                    if device is None or device.v1_properties is None:
                        raise SystemExit("Roboten stoetter ikke V1 kart via dette biblioteket.")
                    await device.v1_properties.start()
                    trait = device.v1_properties.map_content
                    await trait.refresh()
                    if not trait.raw_api_response:
                        raise SystemExit("Roborock returnerte ikke raadata for kartet.")
                    result = save_map_content(trait.raw_api_response, output_file, raw_output_file)
                finally:
                    await manager.close()
            else:
                request_protocol = "rpc" if current_method == "local-rpc" else "general"
                rpc, channel = await get_local_map_rpc(email, device_id, host, request_protocol)
                try:
                    raw_map = await rpc.send_command(RoborockCommand.GET_MAP_V1)
                finally:
                    channel.close()
                if not isinstance(raw_map, bytes):
                    raise SystemExit(f"Uventet kartrespons: {type(raw_map)}")
                result = save_map_content(raw_map, output_file, raw_output_file)
            result["method"] = current_method
            result["host"] = host if current_method != "cloud" else None
            print_json(result)
            return
        except Exception as exc:
            errors.append({"method": current_method, "error": str(exc)})
            continue

    print_json({"ok": False, "errors": errors})
    raise SystemExit("Klarte ikke hente Roborock-kart med noen av metodene.")


async def list_clean_history(email: str, device_id: str | None, host: str, limit: int) -> None:
    from roborock.roborock_typing import RoborockCommand

    rpc, channel = await get_local_rpc(email, device_id, host)
    try:
        summary = await rpc.send_command(RoborockCommand.GET_CLEAN_SUMMARY)
        records = summary.get("records", []) if isinstance(summary, dict) else summary[3]
        result = {
            "host": host,
            "summary": {
                "total_minutes": seconds_to_minutes(summary.get("clean_time")) if isinstance(summary, dict) else None,
                "total_area_m2": area_to_square_meters(summary.get("clean_area")) if isinstance(summary, dict) else None,
                "total_count": summary.get("clean_count") if isinstance(summary, dict) else None,
                "dust_collection_count": summary.get("dust_collection_count") if isinstance(summary, dict) else None,
            },
            "records": [],
        }
        for record_id in records[:limit]:
            raw_record = await rpc.send_command(RoborockCommand.GET_CLEAN_RECORD, params=[record_id])
            raw_items = raw_record if isinstance(raw_record, list) else [raw_record]
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                result["records"].append(
                    {
                        "id": record_id,
                        "begin": item.get("begin"),
                        "begin_local": local_datetime(item.get("begin")),
                        "end": item.get("end"),
                        "end_local": local_datetime(item.get("end")),
                        "duration_seconds": item.get("duration"),
                        "duration_minutes": seconds_to_minutes(item.get("duration")),
                        "area_m2": area_to_square_meters(item.get("area")),
                        "cleaned_area_m2": area_to_square_meters(item.get("cleaned_area")),
                        "complete": item.get("complete"),
                        "error": item.get("error"),
                        "start_type": item.get("start_type"),
                        "clean_type": item.get("clean_type"),
                        "finish_reason": item.get("finish_reason"),
                        "dust_collection_status": item.get("dust_collection_status"),
                        "avoid_count": item.get("avoid_count"),
                        "wash_count": item.get("wash_count"),
                        "clean_times": item.get("clean_times"),
                    }
                )
        print_json(result)
    finally:
        channel.close()


async def cloud_probe(email: str) -> None:
    from roborock.web_api import RoborockApiClient

    user_data = load_user_data()
    web_api = RoborockApiClient(username=email)
    home_data = jsonable(await web_api.get_home_data_v3(user_data))
    devices = home_data.get("devices", []) + home_data.get("received_devices", [])
    products = {product.get("id"): product for product in home_data.get("products", [])}
    result = {
        "home": {
            "id": home_data.get("id"),
            "name": home_data.get("name"),
            "geo_name": home_data.get("geo_name"),
            "lat": home_data.get("lat"),
            "lon": home_data.get("lon"),
            "rooms": home_data.get("rooms", []),
        },
        "cloud_rooms": jsonable(await web_api.get_rooms(user_data)),
        "devices": [],
    }
    for device in devices:
        duid = device.get("duid")
        product = products.get(device.get("product_id"), {})
        item = {
            "name": device.get("name"),
            "duid": duid,
            "source": "received_devices" if device in home_data.get("received_devices", []) else "devices",
            "shared": bool(device.get("share")),
            "online": device.get("online"),
            "firmware": device.get("fv"),
            "protocol_version": device.get("pv"),
            "product": product.get("name"),
            "model": product.get("model"),
            "product_id": device.get("product_id"),
            "room_id": device.get("room_id"),
            "time_zone_id": device.get("time_zone_id"),
            "feature_set": device.get("feature_set"),
            "new_feature_set": device.get("new_feature_set"),
            "status_raw": device.get("device_status"),
        }
        if duid:
            try:
                item["schedules"] = jsonable(await web_api.get_schedules(user_data, duid))
            except Exception as exc:
                item["schedules_error"] = str(exc)
            try:
                item["scenes"] = jsonable(await web_api.get_scenes(user_data, duid))
            except Exception as exc:
                item["scenes_error"] = str(exc)
        result["devices"].append(item)
    print_json(redacted(result))


async def local_read_probe(email: str, device_id: str | None, host: str, include_data: bool) -> None:
    from roborock.roborock_typing import RoborockCommand

    rpc, channel = await get_local_rpc(email, device_id, host)
    results = []
    try:
        for name, command_name, params in LOCAL_READ_COMMANDS:
            command = getattr(RoborockCommand, command_name)
            item = {"name": name, "command": command.value}
            try:
                data = await rpc.send_command(command, params=params)
                item["ok"] = True
                item["type"] = type(data).__name__
                if include_data:
                    item["data"] = jsonable(data)
            except Exception as exc:
                item["ok"] = False
                item["error"] = str(exc)
            results.append(item)
    finally:
        channel.close()
    print_json({"host": host, "results": results})


async def show_status(email: str) -> None:
    manager = await get_device_manager(email)
    devices = await manager.get_devices()
    result = []
    for device in devices:
        item = {
            "name": getattr(device, "name", None),
            "duid": getattr(device, "duid", None),
            "model": getattr(device, "model", None),
        }
        properties = getattr(device, "v1_properties", None)
        if properties and getattr(properties, "status", None):
            await properties.status.refresh()
            item["status"] = jsonable(properties.status)
        if properties and getattr(properties, "consumables", None):
            await properties.consumables.refresh()
            item["consumables"] = jsonable(properties.consumables)
        result.append(item)
    print_json(result)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Roborock API-test for Fibaro10/SUN2.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    request_parser = subparsers.add_parser("request-code", help="Send Roborock innloggingskode på e-post.")
    request_parser.add_argument("--email", required=True)

    request_legacy_parser = subparsers.add_parser(
        "request-code-legacy",
        help="Send Roborock innloggingskode med gammel API-flyt.",
    )
    request_legacy_parser.add_argument("--email", required=True)

    request_probe_parser = subparsers.add_parser(
        "request-code-probe",
        help="Send kode og vis råresponsen fra Roborock.",
    )
    request_probe_parser.add_argument("--email", required=True)
    request_probe_parser.add_argument("--legacy", action="store_true")

    login_parser = subparsers.add_parser("login", help="Logg inn med kode og lagre brukerdata lokalt.")
    login_parser.add_argument("--email", required=True)
    login_parser.add_argument("--code", required=True)
    login_parser.add_argument("--country", help="Eksplisitt landkode, f.eks. NO.")
    login_parser.add_argument("--country-code", type=int, help="Eksplisitt telefonlandkode, f.eks. 47.")

    legacy_parser = subparsers.add_parser("legacy-login", help="Logg inn med gammel e-postkodeflyt.")
    legacy_parser.add_argument("--email", required=True)
    legacy_parser.add_argument("--code", required=True)

    password_parser = subparsers.add_parser("password-login", help="Logg inn med passord og lagre brukerdata lokalt.")
    password_parser.add_argument("--email", required=True)
    password_parser.add_argument("--password", help="Unngå helst denne. Bruk prompt eller --password-env.")
    password_parser.add_argument("--password-env", help="Navn på miljøvariabel som inneholder passordet.")

    password_probe_parser = subparsers.add_parser("password-probe", help="Test passordlogin med eksplisitt totrinnsflagg.")
    password_probe_parser.add_argument("--email", required=True)
    password_probe_parser.add_argument("--password", help="Unngå helst denne. Bruk prompt eller --password-env.")
    password_probe_parser.add_argument("--password-env", help="Navn på miljøvariabel som inneholder passordet.")

    account_parser = subparsers.add_parser("account-info", help="Vis regiondata Roborock bruker for kontoen.")
    account_parser.add_argument("--email", required=True)

    home_parser = subparsers.add_parser("home", help="Hent Roborock home-data via REST.")
    home_parser.add_argument("--email", required=True)

    import_parser = subparsers.add_parser(
        "import-user-data",
        help="Importer Roborock user_data fra JSON eller Home Assistant core.config_entries.",
    )
    import_parser.add_argument("--file", required=True)

    subparsers.add_parser("cache-info", help="Vis lagret Roborock-login uten hemmelige verdier.")

    devices_parser = subparsers.add_parser("devices", help="List Roborock-enheter via rask REST home-data.")
    devices_parser.add_argument("--email", required=True)

    devices_live_parser = subparsers.add_parser("devices-live", help="List Roborock-enheter via full device manager/MQTT.")
    devices_live_parser.add_argument("--email", required=True)

    schedules_parser = subparsers.add_parser("schedules", help="List planlagte Roborock-jobber via REST.")
    schedules_parser.add_argument("--email", required=True)
    schedules_parser.add_argument("--device-id", help="DUID. Kan utelates hvis kontoen bare har én enhet.")

    clean_history_parser = subparsers.add_parser(
        "clean-history",
        help="List siste utførte Roborock-rengjøringer via lokal LAN-tilkobling.",
    )
    clean_history_parser.add_argument("--email", required=True)
    clean_history_parser.add_argument("--device-id", help="DUID. Kan utelates hvis kontoen bare har én enhet.")
    clean_history_parser.add_argument("--host", default=DEFAULT_ROBOROCK_HOST, help="Robotens lokale IP-adresse.")
    clean_history_parser.add_argument("--limit", type=int, default=5, help="Antall siste jobber som skal hentes.")

    cloud_probe_parser = subparsers.add_parser("cloud-probe", help="Hent trygg cloud/REST-oversikt.")
    cloud_probe_parser.add_argument("--email", required=True)

    local_probe_parser = subparsers.add_parser("local-read-probe", help="Test trygge lokale lesekommandoer.")
    local_probe_parser.add_argument("--email", required=True)
    local_probe_parser.add_argument("--device-id", help="DUID. Kan utelates hvis kontoen bare har en enhet.")
    local_probe_parser.add_argument("--host", default=DEFAULT_ROBOROCK_HOST, help="Robotens lokale IP-adresse.")
    local_probe_parser.add_argument("--include-data", action="store_true", help="Ta med rådata i resultatet.")

    map_parser = subparsers.add_parser("map-image", help="Hent Roborock-kart og lagre det som PNG.")
    map_parser.add_argument("--email", required=True)
    map_parser.add_argument("--device-id", help="DUID. Kan utelates hvis kontoen bare har en enhet.")
    map_parser.add_argument("--host", default=DEFAULT_ROBOROCK_HOST, help="Robotens lokale IP-adresse.")
    map_parser.add_argument("--output", default="roborock_output/map.png", help="PNG-fil som skal skrives.")
    map_parser.add_argument("--raw-output", help="Valgfri fil for raadata fra Roborock.")
    map_parser.add_argument(
        "--method",
        choices=["auto", "local-rpc", "local-general", "cloud"],
        default="cloud",
        help="Hvilken kanal som skal testes.",
    )

    status_parser = subparsers.add_parser("status", help="Hent status og forbruksdeler for støvsugere.")
    status_parser.add_argument("--email", required=True)

    args = parser.parse_args()

    if args.command == "request-code":
        await request_code(args.email)
    elif args.command == "request-code-probe":
        await request_code_probe(args.email, args.legacy)
    elif args.command == "request-code-legacy":
        await request_code_legacy(args.email)
    elif args.command == "login":
        if args.country or args.country_code:
            if not args.country or args.country_code is None:
                raise SystemExit("Bruk både --country og --country-code, eller ingen av dem.")
            await login_explicit(args.email, args.code, args.country, args.country_code)
        else:
            await login(args.email, args.code)
    elif args.command == "password-login":
        await password_login(args.email, args.password, args.password_env)
    elif args.command == "password-probe":
        await password_probe(args.email, args.password, args.password_env)
    elif args.command == "legacy-login":
        await legacy_login(args.email, args.code)
    elif args.command == "account-info":
        await account_info(args.email)
    elif args.command == "home":
        await show_home(args.email)
    elif args.command == "import-user-data":
        import_user_data(args.file)
    elif args.command == "cache-info":
        cache_info()
    elif args.command == "devices":
        await list_devices(args.email)
    elif args.command == "devices-live":
        await list_devices_live(args.email)
    elif args.command == "schedules":
        await list_schedules(args.email, args.device_id)
    elif args.command == "clean-history":
        await list_clean_history(args.email, args.device_id, args.host, args.limit)
    elif args.command == "cloud-probe":
        await cloud_probe(args.email)
    elif args.command == "local-read-probe":
        await local_read_probe(args.email, args.device_id, args.host, args.include_data)
    elif args.command == "map-image":
        await fetch_map_image(args.email, args.device_id, args.host, args.output, args.raw_output, args.method)
    elif args.command == "status":
        await show_status(args.email)


if __name__ == "__main__":
    try:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except ModuleNotFoundError as exc:
        if exc.name == "roborock":
            raise SystemExit(
                "Python-pakken mangler. Installer først:\n"
                "  python -m pip install python-roborock"
            ) from exc
        raise
