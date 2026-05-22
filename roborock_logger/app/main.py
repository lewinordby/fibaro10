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
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

load_dotenv()

DATA_DIR = Path(os.getenv("ROBOROCK_DATA_DIR", "./data"))
CACHE_FILE = DATA_DIR / "roborock_user_data.pickle"
CLIENT_IDS_FILE = DATA_DIR / "roborock_client_ids.json"
STATE_FILE = DATA_DIR / "state.json"
QUEUE_FILE = DATA_DIR / "pending_batches.jsonl"

ROBOROCK_EMAIL = os.getenv("ROBOROCK_EMAIL", "roborock.sun2@gmail.com")
ROBOROCK_SUBNET = os.getenv("ROBOROCK_SUBNET", "192.168.2.")
COLLECTOR_ID = os.getenv("COLLECTOR_ID", "roborock_logger")
FIBARO10_API_BASE_URL = os.getenv("FIBARO10_API_BASE_URL", "https://fibaro10.onrender.com").rstrip("/")
FIBARO10_API_USERNAME = os.getenv("FIBARO10_API_USERNAME", "")
FIBARO10_API_PASSWORD = os.getenv("FIBARO10_API_PASSWORD", "")
STATUS_INTERVAL_SECONDS = int(os.getenv("STATUS_INTERVAL_SECONDS", "300"))
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "10"))
MAP_SYNC_ON_START = os.getenv("MAP_SYNC_ON_START", "true").lower() in {"1", "true", "yes", "on"}
AUTO_SYNC_ENABLED = os.getenv("AUTO_SYNC_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
ROBOROCK_LOCAL_PORT = 58867

app = FastAPI(title="Roborock_logger")
sync_lock = asyncio.Lock()


def utc_now() -> dt.datetime:
    return dt.datetime.utcnow().replace(microsecond=0)


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


def load_state() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"robots": {}, "last_sync": None, "last_error": None, "pending_batches": 0}


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


async def get_home_data(email: str) -> dict[str, Any]:
    web_api = create_web_api(email)
    return jsonable(await web_api.get_home_data_v3(load_user_data()))


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


def post_to_fibaro10(batch: dict[str, Any]) -> None:
    url = f"{FIBARO10_API_BASE_URL}/api/renhold/ingest"
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


def queue_batch(batch: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with QUEUE_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(batch, ensure_ascii=False) + "\n")


def resend_queue() -> int:
    if not QUEUE_FILE.exists():
        return 0
    lines = QUEUE_FILE.read_text(encoding="utf-8").splitlines()
    remaining = []
    sent = 0
    for line in lines:
        if not line.strip():
            continue
        batch = json.loads(line)
        try:
            post_to_fibaro10(batch)
            sent += 1
        except Exception:
            remaining.append(line)
    QUEUE_FILE.write_text("\n".join(remaining) + ("\n" if remaining else ""), encoding="utf-8")
    return sent


async def collect_once(include_maps: bool = False) -> dict[str, Any]:
    home = await get_home_data(ROBOROCK_EMAIL)
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
                host, network, probes = await find_local_host(device, candidates)
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
            "last_status": utc_now().isoformat(),
            "online": robot.get("online"),
            "last_error": robot.get("last_error"),
        }
    batch = {
        "source": "Roborock_logger",
        "collector_id": COLLECTOR_ID,
        "timestamp": utc_now().isoformat(),
        "ok": True,
        "robots": robots,
        "extra": {"home_id": home.get("id"), "host_candidates": candidates},
    }
    try:
        resend_queue()
        post_to_fibaro10(batch)
        state["last_sync"] = utc_now().isoformat()
        state["last_error"] = None
    except Exception as exc:
        queue_batch(batch)
        state["last_error"] = str(exc)
    state["pending_batches"] = sum(1 for _ in QUEUE_FILE.open(encoding="utf-8")) if QUEUE_FILE.exists() else 0
    save_state(state)
    return batch


async def sync_loop() -> None:
    first = True
    while True:
        try:
            if AUTO_SYNC_ENABLED and CACHE_FILE.exists():
                async with sync_lock:
                    await collect_once(include_maps=first and MAP_SYNC_ON_START)
                first = False
        except Exception as exc:
            state = load_state()
            state["last_error"] = str(exc)
            save_state(state)
        await asyncio.sleep(max(60, STATUS_INTERVAL_SECONDS))


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
<div class="metric"><span>Kø</span><strong>{state.get('pending_batches', 0)}</strong></div>
</div><p>Siste feil: <code>{state.get('last_error') or '-'}</code></p></section>
<section class="panel"><h2>Handlinger</h2>
<p><a class="button" href="/sync-now">Synk nå</a> <a class="button" href="/sync-now?maps=true">Synk med kart</a> <a class="button" href="/api/status">JSON status</a></p>
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
async def sync_now(maps: bool = False):
    async with sync_lock:
        batch = await collect_once(include_maps=maps)
    return JSONResponse({"status": "ok", "robots": len(batch.get("robots", []))})


@app.get("/api/status")
async def status():
    return load_state()


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
