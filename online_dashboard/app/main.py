from datetime import date, datetime, timedelta
import hmac
import hashlib
from html import escape
import asyncio
import json
import os
import re
import time
from typing import Any, Optional
from urllib.parse import quote, quote_plus, urlencode, urlparse
import urllib.request
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+asyncpg://" + DATABASE_URL.removeprefix("postgres://")
elif DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+asyncpg://" + DATABASE_URL.removeprefix("postgresql://")
LOCAL_TZ = ZoneInfo("Europe/Oslo")
AUTH_USER_COOKIE_NAME = "fibaro10_access_username"
AUTH_COOKIE_NAME = "fibaro10_access_password"
SNAPSHOT_SESSION_COOKIE_NAME = "lilletorget_online_session"
PUBLIC_PATHS = {"/health", "/favicon.ico", "/auth/login"}
PUBLIC_PREFIXES = ("/static/",)
ACCESS_FAILED_DISABLE_THRESHOLD = max(1, int(os.getenv("ACCESS_FAILED_DISABLE_THRESHOLD", "3")))
ONLINE_ACCESS_LOG_COOLDOWN_SECONDS = max(0, int(os.getenv("ONLINE_ACCESS_LOG_COOLDOWN_SECONDS", "0")))
EASYPARK_DOWNLOADER_URL = os.getenv("EASYPARK_DOWNLOADER_URL", "http://192.168.20.218:8109").rstrip("/")
EASYPARK_DOWNLOADER_TIMEOUT_SECONDS = max(60, int(os.getenv("EASYPARK_DOWNLOADER_TIMEOUT_SECONDS", "360")))
EASYPARK_REFRESH_RETRY_WAIT_SECONDS = max(0, int(os.getenv("EASYPARK_REFRESH_RETRY_WAIT_SECONDS", "30")))
PARKING_REFRESH_COOLDOWN_SECONDS = max(0, int(os.getenv("PARKING_REFRESH_COOLDOWN_SECONDS", "180")))
ONLINE_DASHBOARD_MODE = os.getenv("ONLINE_DASHBOARD_MODE", "source").strip().lower()
SNAPSHOT_MODE = ONLINE_DASHBOARD_MODE == "snapshot"
SOURCE_MODE = not SNAPSHOT_MODE
PUBLIC_DASHBOARD_PUBLIC = os.getenv("PUBLIC_DASHBOARD_PUBLIC", "0").strip().lower() in {"1", "true", "yes", "on"}
PUBLIC_DASHBOARD_SHOW_MONEY = os.getenv("PUBLIC_DASHBOARD_SHOW_MONEY", "0").strip().lower() in {"1", "true", "yes", "on"}
PUBLIC_DASHBOARD_USERNAME = os.getenv("PUBLIC_DASHBOARD_USERNAME", "").strip()
PUBLIC_DASHBOARD_PASSWORD = os.getenv("PUBLIC_DASHBOARD_PASSWORD", "")
PUBLIC_DASHBOARD_SESSION_SECRET = os.getenv("PUBLIC_DASHBOARD_SESSION_SECRET", "")
PUBLIC_DASHBOARD_INGEST_TOKEN = os.getenv("PUBLIC_DASHBOARD_INGEST_TOKEN", "")
PUBLIC_DASHBOARD_SYNC_ENABLED = os.getenv("PUBLIC_DASHBOARD_SYNC_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
PUBLIC_DASHBOARD_SYNC_URL = os.getenv("PUBLIC_DASHBOARD_SYNC_URL", "").strip()
PUBLIC_DASHBOARD_SYNC_TOKEN = os.getenv("PUBLIC_DASHBOARD_SYNC_TOKEN", "")
PUBLIC_DASHBOARD_SYNC_INTERVAL_SECONDS = max(5, int(os.getenv("PUBLIC_DASHBOARD_SYNC_INTERVAL_SECONDS", "15")))
PUBLIC_DASHBOARD_SYNC_TIMEOUT_SECONDS = max(3, int(os.getenv("PUBLIC_DASHBOARD_SYNC_TIMEOUT_SECONDS", "12")))
PUBLIC_DASHBOARD_SNAPSHOT_NAME = os.getenv("PUBLIC_DASHBOARD_SNAPSHOT_NAME", "current").strip() or "current"
MASTER_ACCESS_KEY_HASH = os.getenv("MASTER_ACCESS_KEY_HASH", "").strip()
NTFY_BASE_URL = os.getenv("NTFY_BASE_URL", "https://ntfy.sh").rstrip("/")
DEFAULT_NTFY_DOORS_TOPIC = f"sun2-dorer-{MASTER_ACCESS_KEY_HASH[:12]}" if MASTER_ACCESS_KEY_HASH else "sun2-dorer"
NTFY_DOORS_TOPIC = os.getenv("NTFY_DOORS_TOPIC", DEFAULT_NTFY_DOORS_TOPIC).strip() or DEFAULT_NTFY_DOORS_TOPIC
SUNROOM_DOOR_SESSION_GRACE_MINUTES = float(os.getenv("SUNROOM_DOOR_SESSION_GRACE_MINUTES", "5"))
SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES = float(os.getenv("SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES", "8"))
SUNROOM_DOOR_PAYMENT_DELAY_MINUTES = float(os.getenv("SUNROOM_DOOR_PAYMENT_DELAY_MINUTES", "3"))
SUNROOM_DOOR_EXIT_GRACE_MINUTES = float(os.getenv("SUNROOM_DOOR_EXIT_GRACE_MINUTES", "3"))
SUNROOM_DOOR_WARN_AFTER_END_MINUTES = float(os.getenv("SUNROOM_DOOR_WARN_AFTER_END_MINUTES", "5"))
SUNROOM_DOOR_ALERT_AFTER_END_MINUTES = float(os.getenv("SUNROOM_DOOR_ALERT_AFTER_END_MINUTES", "10"))
HC3_DOOR_DEBOUNCE_SECONDS = max(0.0, float(os.getenv("HC3_DOOR_DEBOUNCE_SECONDS", "5")))

SOLROOM_DOOR_CONFIG = [
    {"device_id": 459, "device_key": "door_solrom_01", "title": "Solrom 1", "section_title": "1.etg", "group_key": "solrom", "sort_order": 1, "room_id": "rom-01", "sun2_bed_id": "640"},
    {"device_id": None, "device_key": "door_solrom_02", "title": "Solrom 2", "section_title": "1.etg", "group_key": "solrom", "sort_order": 2, "room_id": "rom-02", "sun2_bed_id": "641"},
    {"device_id": None, "device_key": "door_solrom_03", "title": "Solrom 3", "section_title": "1.etg", "group_key": "solrom", "sort_order": 3, "room_id": "rom-03", "sun2_bed_id": "642"},
    {"device_id": 465, "device_key": "door_solrom_04", "title": "Solrom 4", "section_title": "2.etg", "group_key": "solrom", "sort_order": 4, "room_id": "rom-04", "sun2_bed_id": "643"},
    {"device_id": 463, "device_key": "door_solrom_05", "title": "Solrom 5", "section_title": "2.etg", "group_key": "solrom", "sort_order": 5, "room_id": "rom-05", "sun2_bed_id": "644"},
    {"device_id": 469, "device_key": "door_solrom_06", "title": "Solrom 6", "section_title": "2.etg", "group_key": "solrom", "sort_order": 6, "room_id": "rom-06", "sun2_bed_id": "645"},
    {"device_id": 471, "device_key": "door_solrom_07", "title": "Solrom 7", "section_title": "2.etg", "group_key": "solrom", "sort_order": 7, "room_id": "rom-07", "sun2_bed_id": "646"},
    {"device_id": 473, "device_key": "door_solrom_08", "title": "Solrom 8", "section_title": "2.etg", "group_key": "solrom", "sort_order": 8, "room_id": "rom-08", "sun2_bed_id": "647"},
    {"device_id": 475, "device_key": "door_solrom_09", "title": "Solrom 9", "section_title": "1.etg", "group_key": "solrom", "sort_order": 9, "room_id": "rom-09", "sun2_bed_id": "648"},
    {"device_id": 477, "device_key": "door_solrom_10", "title": "Solrom 10", "section_title": "VIP", "group_key": "solrom", "sort_order": 10, "room_id": "rom-11", "sun2_bed_id": "679"},
    {"device_id": 479, "device_key": "door_solrom_11", "title": "Solrom 11", "section_title": "VIP", "group_key": "solrom", "sort_order": 11, "room_id": "rom-12", "sun2_bed_id": "680"},
    {"device_id": 491, "device_key": "door_solrom_12", "title": "Solrom 12", "section_title": "VIP", "group_key": "solrom", "sort_order": 12, "room_id": "rom-13", "sun2_bed_id": "681"},
]
SOLROOM_DOOR_DEVICE_IDS = [int(item["device_id"]) for item in SOLROOM_DOOR_CONFIG if item.get("device_id") is not None]
SOLROOM_DOOR_KEYS = [str(item["device_key"]) for item in SOLROOM_DOOR_CONFIG if item.get("device_key")]
SOLROOM_DOOR_BY_KEY = {str(item["device_key"]): item for item in SOLROOM_DOOR_CONFIG}

OTHER_DOOR_CONFIG = [
    {"device_id": 453, "device_key": "door_453", "title": "Bod/kjøkken", "sort_order": 101},
    {"device_id": 447, "device_key": "door_447", "title": "Kjeller luke", "sort_order": 102},
    {"device_id": 413, "device_key": "door_413", "title": "Arbeidsrom", "sort_order": 103},
    {"device_id": 499, "device_key": "door_inngang", "title": "Inngang", "sort_order": 104},
    {"device_id": 483, "device_key": "door_massasjestudio", "title": "Massasjestudio", "sort_order": 105},
    {"device_id": 535, "device_key": "door_loftluke_massasje", "title": "Loftluke massasje", "sort_order": 106},
    {"device_id": 489, "device_key": "door_vaskerom", "title": "Vaskerom", "sort_order": 107},
    {"device_id": 487, "device_key": "door_papirlager", "title": "Papirlager", "sort_order": 108},
    {"device_id": 493, "device_key": "door_vaktmesterlager", "title": "Vaktmesterlager", "sort_order": 109},
    {"device_id": 495, "device_key": "door_toalett", "title": "Toalett", "sort_order": 110},
]
OTHER_DOOR_DEVICE_IDS = [int(item["device_id"]) for item in OTHER_DOOR_CONFIG if item.get("device_id") is not None]
OTHER_DOOR_KEYS = [str(item["device_key"]) for item in OTHER_DOOR_CONFIG if item.get("device_key")]
OTHER_DOOR_BY_KEY = {str(item["device_key"]): item for item in OTHER_DOOR_CONFIG}

app = FastAPI(title="Lilletorget online", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)
parking_refresh_lock = asyncio.Lock()
parking_refresh_last_started_monotonic: Optional[float] = None
public_dashboard_sync_task: Optional[asyncio.Task] = None

SNAPSHOT_TABLE_SQL = """
create table if not exists online_dashboard_snapshots (
    name text primary key,
    payload jsonb not null,
    payload_hash text not null,
    source_published_at timestamp null,
    received_at timestamp not null default now()
)
"""


def public_access_key() -> dict[str, Any]:
    return {
        "id": 0,
        "name": "public-dashboard",
        "key_prefix": "public",
        "role": "settings" if PUBLIC_DASHBOARD_SHOW_MONEY else "viewer",
        "is_master": PUBLIC_DASHBOARD_SHOW_MONEY,
        "active": True,
    }


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=json_safe)


def json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "as_tuple"):
        return float(value)
    return str(value)


def hydrate_value(value: Any) -> Any:
    if isinstance(value, list):
        return [hydrate_value(item) for item in value]
    if isinstance(value, dict):
        return {key: hydrate_value(item) for key, item in value.items()}
    if isinstance(value, str):
        try:
            if "T" in value or (" " in value and ":" in value):
                return datetime.fromisoformat(value)
            if len(value) == 10 and value[4] == "-" and value[7] == "-":
                return date.fromisoformat(value)
        except ValueError:
            return value
    return value


def snapshot_session_secret() -> str:
    return PUBLIC_DASHBOARD_SESSION_SECRET or PUBLIC_DASHBOARD_PASSWORD


def snapshot_session_token(username: str) -> str:
    issued_at = str(int(time.time()))
    message = f"{username}\0{issued_at}"
    signature = hmac.new(snapshot_session_secret().encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{username}:{issued_at}:{signature}"


def valid_snapshot_session(request: Request) -> bool:
    token = request.cookies.get(SNAPSHOT_SESSION_COOKIE_NAME, "")
    if not token or not snapshot_session_secret():
        return False
    try:
        username, issued_at, signature = token.split(":", 2)
        issued_i = int(issued_at)
    except ValueError:
        return False
    if username != normalize_username(PUBLIC_DASHBOARD_USERNAME):
        return False
    if time.time() - issued_i > 60 * 60 * 24 * 30:
        return False
    expected = hmac.new(snapshot_session_secret().encode("utf-8"), f"{username}\0{issued_at}".encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


def normalize_username(value: str) -> str:
    return value.strip().casefold()


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def credential_hash(username: str, password: str) -> str:
    return hash_value(normalize_username(username) + "\0" + password)


def local_now() -> datetime:
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)


def day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, datetime.min.time())
    return start, start + timedelta(days=1)


def fmt_int(value: Any) -> str:
    try:
        return f"{int(value or 0):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


def fmt_money(value: Any) -> str:
    try:
        return f"{float(value or 0):,.0f} kr".replace(",", " ")
    except (TypeError, ValueError):
        return "0 kr"


def fmt_amount(value: Any) -> str:
    try:
        return f"{float(value or 0):,.0f}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


def fmt_temp(value: Any) -> str:
    try:
        return f"{float(value):.1f}°"
    except (TypeError, ValueError):
        return "-"


def fmt_watt(value: Any) -> str:
    try:
        watts = float(value or 0)
    except (TypeError, ValueError):
        return "0 W"
    if abs(watts) >= 1000:
        return f"{watts / 1000:.1f} kW".replace(".", ",")
    return f"{watts:.0f} W".replace(".", ",")


def fmt_kwh(value: Any) -> str:
    try:
        return f"{float(value or 0):.1f} kWh".replace(".", ",")
    except (TypeError, ValueError):
        return "0,0 kWh"


def fmt_time(value: Any) -> str:
    if not isinstance(value, datetime):
        return "-"
    return value.strftime("%d.%m %H:%M")


def fmt_date(value: Any) -> str:
    if not isinstance(value, datetime):
        return "-"
    return value.strftime("%d.%m.%Y")


def fmt_clock(value: Any) -> str:
    if not isinstance(value, datetime):
        return "-"
    return value.strftime("kl. %H:%M")


def display_stamp(value: Any) -> str:
    if not isinstance(value, datetime):
        return "-"
    return value.strftime("%d.%m kl. %H:%M")


def ntfy_host() -> str:
    parsed = urlparse(NTFY_BASE_URL)
    return parsed.netloc or parsed.path.strip("/")


def ntfy_topic_url(topic: str) -> str:
    return f"{NTFY_BASE_URL}/{quote(topic, safe='')}"


def ntfy_subscribe_url(topic: str, display_name: str) -> str:
    return f"ntfy://{ntfy_host()}/{quote(topic, safe='')}?display={quote_plus(display_name)}"


def easypark_next_run_at(status: dict[str, Any]) -> Optional[datetime]:
    schedule = status.get("schedule") if isinstance(status, dict) else None
    raw_value = schedule.get("next_run_at") if isinstance(schedule, dict) else status.get("next_run_at")
    if not raw_value:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw_value))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return parsed


def format_duration_short(seconds: int) -> str:
    if seconds <= 60:
        return "under 1 min"
    minutes = (seconds + 59) // 60
    return f"{minutes} min"


def parking_refresh_cooldown_remaining_seconds() -> int:
    if PARKING_REFRESH_COOLDOWN_SECONDS <= 0 or parking_refresh_last_started_monotonic is None:
        return 0
    elapsed = time.monotonic() - parking_refresh_last_started_monotonic
    return max(0, int(PARKING_REFRESH_COOLDOWN_SECONDS - elapsed + 0.999))


def fmt_utc_time(value: Any) -> str:
    if not isinstance(value, datetime):
        return "-"
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(LOCAL_TZ).strftime("%d.%m %H:%M")


def state_label(value: Any) -> str:
    if value is True:
        return "PÅ"
    if value is False:
        return "AV"
    return "-"


def state_class(value: Any) -> str:
    if value is True:
        return "is-on"
    if value is False:
        return "is-off"
    return "is-unknown"


def presented_credentials(request: Request) -> tuple[Optional[str], Optional[str]]:
    return (
        request.cookies.get(AUTH_USER_COOKIE_NAME),
        request.cookies.get(AUTH_COOKIE_NAME),
    )


async def find_access_key(username: Optional[str], password: Optional[str]) -> Optional[dict[str, Any]]:
    if not username or not password:
        return None
    normalized = normalize_username(username)
    hashed = hash_value(password) if normalized == "master" else credential_hash(normalized, password)
    async with async_session() as session:
        row = (
            await session.execute(
                text(
                    """
                    select id, name, key_prefix, role, is_master, active
                    from access_keys
                    where name = :name and key_hash = :hash and active = true
                    limit 1
                    """
                ),
                {"name": normalized, "hash": hashed},
            )
        ).mappings().first()
        return dict(row) if row else None


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else ""


async def should_log_online_activity(request: Request, access_key: dict[str, Any]) -> bool:
    if request.method != "GET" or not wants_html(request):
        return False
    if request.url.path.startswith("/auth/"):
        return False
    if ONLINE_ACCESS_LOG_COOLDOWN_SECONDS <= 0:
        return True
    async with async_session() as session:
        row = (
            await session.execute(
                text(
                    """
                    select timestamp
                    from access_logs
                    where access_key_id = :access_key_id
                      and success = true
                      and reason = 'online_dashboard'
                      and path = :path
                    order by timestamp desc, id desc
                    limit 1
                    """
                ),
                {"access_key_id": access_key["id"], "path": request.url.path},
            )
        ).mappings().first()
    if not row or not isinstance(row.get("timestamp"), datetime):
        return True
    return datetime.utcnow() - row["timestamp"] >= timedelta(seconds=ONLINE_ACCESS_LOG_COOLDOWN_SECONDS)


async def touch_access_key(access_key: dict[str, Any], request: Request) -> None:
    async with async_session() as session:
        await session.execute(
            text(
                """
                update access_keys
                set last_seen_at = :now,
                    last_ip = :ip,
                    last_user_agent = :user_agent,
                    uses_count = coalesce(uses_count, 0) + 1
                where id = :id
                """
            ),
            {
                "now": datetime.utcnow(),
                "id": access_key["id"],
                "ip": client_ip(request),
                "user_agent": request.headers.get("user-agent", ""),
            },
        )
        await session.commit()


async def log_access_attempt(
    request: Request,
    success: bool,
    reason: str,
    access_key: Optional[dict[str, Any]] = None,
    attempted_username: Optional[str] = None,
) -> None:
    key_name = access_key["name"] if access_key else normalize_username(attempted_username or "") or None
    key_prefix = access_key.get("key_prefix") if access_key else None
    final_reason = reason
    async with async_session() as session:
        insert_result = await session.execute(
            text(
                """
                insert into access_logs
                    (timestamp, access_key_id, key_name, key_prefix, path, method, ip, user_agent, success, reason)
                values
                    (:timestamp, :access_key_id, :key_name, :key_prefix, :path, :method, :ip, :user_agent, :success, :reason)
                returning id
                """
            ),
            {
                "timestamp": datetime.utcnow(),
                "access_key_id": access_key["id"] if access_key else None,
                "key_name": key_name,
                "key_prefix": key_prefix,
                "path": request.url.path,
                "method": request.method,
                "ip": client_ip(request),
                "user_agent": request.headers.get("user-agent", ""),
                "success": success,
                "reason": final_reason,
            },
        )
        log_id = insert_result.scalar_one()
        if access_key and success:
            await session.execute(
                text(
                    """
                    update access_keys
                    set last_seen_at = :now,
                        last_ip = :ip,
                        last_user_agent = :user_agent,
                        uses_count = coalesce(uses_count, 0) + 1
                    where id = :id
                    """
                ),
                {
                    "now": datetime.utcnow(),
                    "id": access_key["id"],
                    "ip": client_ip(request),
                    "user_agent": request.headers.get("user-agent", ""),
                },
            )
        elif not success and key_name and key_name != "master":
            user_row = (
                await session.execute(
                    text(
                        """
                        select id, key_prefix
                        from access_keys
                        where name = :name and is_master = false and active = true
                        order by id desc
                        limit 1
                        """
                    ),
                    {"name": key_name},
                )
            ).mappings().first()
            if user_row:
                recent_failures = (
                    await session.execute(
                        text(
                            """
                            select success
                            from access_logs
                            where key_name = :name
                            order by timestamp desc, id desc
                            limit :limit
                            """
                        ),
                        {"name": key_name, "limit": ACCESS_FAILED_DISABLE_THRESHOLD},
                    )
                ).scalars().all()
                if len(recent_failures) >= ACCESS_FAILED_DISABLE_THRESHOLD and all(value is False for value in recent_failures):
                    final_reason = f"{reason}_auto_deactivated_after_{ACCESS_FAILED_DISABLE_THRESHOLD}_failures"
                    await session.execute(
                        text(
                            """
                            update access_keys
                            set active = false
                            where id = :id
                            """
                        ),
                        {"id": user_row["id"]},
                    )
                    await session.execute(
                        text(
                            """
                            update access_logs
                            set access_key_id = :access_key_id,
                                key_prefix = :key_prefix,
                                reason = :reason
                            where id = :log_id
                            """
                        ),
                        {
                            "log_id": log_id,
                            "access_key_id": user_row["id"],
                            "key_prefix": user_row["key_prefix"],
                            "reason": final_reason,
                        },
                    )
        await session.commit()


def wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept or "*/*" in accept


def compare_text(current: Any, previous: Any, noun: str = "") -> str:
    try:
        current_i = int(current or 0)
        previous_i = int(previous or 0)
    except (TypeError, ValueError):
        return "I går -"
    diff = current_i - previous_i
    if diff == 0:
        return f"Lik som i går ({fmt_int(previous_i)}{noun})"
    sign = "+" if diff > 0 else "-"
    return f"{sign}{fmt_int(abs(diff))}{noun} mot i går ({fmt_int(previous_i)})"


def compare_short(current: Any, previous: Any, label: str) -> str:
    try:
        current_i = int(current or 0)
        previous_i = int(previous or 0)
    except (TypeError, ValueError):
        return "-"
    diff = current_i - previous_i
    if diff == 0:
        return f"Lik mot {label}"
    sign = "+" if diff > 0 else "-"
    return f"{sign}{fmt_int(abs(diff))} mot {label}"


def operating_window(now: datetime) -> dict[str, Any]:
    open_at = datetime.combine(now.date(), datetime.min.time()).replace(hour=7)
    close_at = datetime.combine(now.date(), datetime.min.time()).replace(hour=23)
    if now < open_at:
        return {"label": "Stengt", "detail": "Åpner 07:00", "progress": 0}
    if now >= close_at:
        return {"label": "Stengt", "detail": "Stengte 23:00", "progress": 100}
    total_seconds = (close_at - open_at).total_seconds()
    progress = int(((now - open_at).total_seconds() / total_seconds) * 100)
    return {"label": "Åpent", "detail": "Stenger 23:00", "progress": max(0, min(100, progress))}


def can_manage(access_key: dict[str, Any]) -> bool:
    role = "master" if access_key.get("is_master") else (access_key.get("role") or "viewer").strip().lower()
    return role in {"master", "settings"}


def money_if_allowed(access_key: dict[str, Any], value: Any) -> str:
    return fmt_money(value) if can_manage(access_key) else ""


def easypark_period() -> tuple[date, date]:
    today = local_now().date()
    return today - timedelta(days=1), today


def easypark_downloader_request(
    path: str,
    params: dict[str, Any],
    timeout_seconds: int = EASYPARK_DOWNLOADER_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    query = urlencode({key: value for key, value in params.items() if value is not None})
    url = f"{EASYPARK_DOWNLOADER_URL}{path}"
    if query:
        url = f"{url}?{query}"
    request = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read().decode("utf-8", errors="replace")
    return json.loads(payload)


def easypark_downloader_status() -> dict[str, Any]:
    try:
        with urllib.request.urlopen(f"{EASYPARK_DOWNLOADER_URL}/status", timeout=2) as response:
            payload = response.read().decode("utf-8", errors="replace")
        return json.loads(payload)
    except Exception:
        return {}


def classify_easypark_error(message: Any) -> str:
    if not message:
        return ""
    normalized = str(message).casefold()
    if "launch_persistent_context" in normalized or ("browser" in normalized and "timeout" in normalized):
        return "browser_timeout"
    if "easypark-importen stoppet etter" in normalized:
        return "job_timeout"
    if "target page, context or browser has been closed" in normalized:
        return "browser_closed"
    if "timed out" in normalized or "timeout" in normalized:
        return "timeout"
    return "unknown"


def friendly_easypark_error(reason: str, status: dict[str, Any]) -> str:
    status_reason = classify_easypark_error(status.get("last_error"))
    code = reason or status_reason
    messages = {
        "browser_timeout": "EasyPark-browseren startet ikke innen tidsfristen. Containeren restartes automatisk.",
        "job_timeout": "EasyPark-importen brukte for lang tid. Containeren restartes automatisk.",
        "browser_closed": "EasyPark-browseren lukket seg under import. Prøv igjen om litt.",
        "timeout": "EasyPark svarte ikke innen tidsfristen.",
        "unavailable": "EasyPark-importøren svarte ikke akkurat nå.",
        "unknown": "Se siste EasyPark-status under knappen.",
    }
    return messages.get(code, messages["unknown"])


def should_retry_easypark_refresh(reason: str) -> bool:
    return reason in {"browser_timeout", "job_timeout", "browser_closed", "timeout", "unavailable"}


async def wait_for_easypark_ready(timeout_seconds: int = EASYPARK_REFRESH_RETRY_WAIT_SECONDS) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_status: dict[str, Any] = {}
    while time.monotonic() <= deadline:
        last_status = await asyncio.to_thread(easypark_downloader_status)
        if last_status and last_status.get("running") is not True:
            return last_status
        await asyncio.sleep(2)
    return last_status


def short_message(value: Any, max_length: int = 110) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3].rstrip()}..."


def first_value(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def car_info_fields(data: Any) -> dict[str, Any]:
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return {}
    if not isinstance(data, dict):
        return {}
    fields = data.get("fields")
    return fields if isinstance(fields, dict) else {}


def car_info_field_value(data: Any, *keys: str) -> Any:
    fields = car_info_fields(data)
    for key in keys:
        value = fields.get(key)
        if value not in (None, ""):
            return value
    return None


def car_info_vehicle_title(data: Any) -> Optional[str]:
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return None
    if not isinstance(data, dict):
        return None
    return first_value(
        car_info_field_value(data, "vehicle_title"),
        data.get("vehicle_title"),
        data.get("title"),
    )


def parking_vehicle_label_is_unknown(value: Optional[str]) -> bool:
    text_value = (value or "").strip().lower()
    return not text_value or text_value.startswith("ukjent")


def year_from_value(value: Any) -> Optional[int]:
    if isinstance(value, datetime):
        return value.year
    if isinstance(value, date):
        return value.year
    text_value = str(value or "")
    match = re.search(r"(19|20)\d{2}", text_value)
    return int(match.group(0)) if match else None


def parking_vehicle_summary(row: dict[str, Any]) -> str:
    label = " ".join(
        str(part).strip()
        for part in [row.get("merke"), row.get("modell"), row.get("typebetegnelse")]
        if str(part or "").strip()
    )
    if parking_vehicle_label_is_unknown(label):
        label = car_info_vehicle_title(row.get("car_info_data")) or ""
    if parking_vehicle_label_is_unknown(label):
        return "Ukjent kjøretøy"
    year = (
        year_from_value(row.get("forstegangsregistrert_norge"))
        or year_from_value(row.get("svv_teknisk_gyldig_fra"))
        or year_from_value(car_info_field_value(row.get("car_info_data"), "model_year", "first_registered", "first_registration"))
    )
    color = str(first_value(row.get("farge"), car_info_field_value(row.get("car_info_data"), "color")) or "").strip()
    summary = f"{year} {label}" if year else label
    return f"{summary} - {color}" if color else summary


def parking_status_label(value: Any) -> str:
    status = str(value or "").strip()
    return {
        "active": "P\u00e5g\u00e5r",
        "ongoing": "P\u00e5g\u00e5r",
        "ended": "Avsluttet",
        "completed": "Avsluttet",
        "finished": "Avsluttet",
    }.get(status.casefold(), status)


def parking_status_is_active(value: Any) -> bool:
    return str(value or "").strip().casefold() in {
        "active",
        "aktiv",
        "ongoing",
        "p\u00e5g\u00e5ende",
        "p\u00e5g\u00e5r",
        "started",
    }


def parking_previous_count_label(value: Any) -> str:
    try:
        count = max(0, int(value or 0))
    except (TypeError, ValueError):
        count = 0
    if count == 0:
        return "F\u00f8rste parkering"
    if count == 1:
        return "Parkert 1 gang f\u00f8r"
    return f"Parkert {fmt_int(count)} ganger f\u00f8r"


def door_config_match(row: dict[str, Any], config: dict[str, Any]) -> bool:
    device_id = row.get("device_id")
    if device_id is not None and config.get("device_id") is not None:
        try:
            if int(device_id) == int(config["device_id"]):
                return True
        except (TypeError, ValueError):
            pass
    return str(row.get("device_key") or "") == str(config.get("device_key") or "")


def door_state_info(row: Optional[dict[str, Any]]) -> dict[str, str]:
    if not row:
        return {"state": "unknown", "label": "Ukjent", "tone": "unknown"}
    action = str(row.get("action") or "").strip().upper()
    raw_value = str(row.get("raw_value") or "").strip().lower()
    state = row.get("state")
    if state is True or action in {"OPEN", "OPENED", "ÅPEN", "APEN"} or raw_value in {"true", "1", "open", "opened"}:
        return {"state": "open", "label": "Åpen", "tone": "warn"}
    if state is False or action in {"CLOSED", "CLOSE", "LUKKET"} or raw_value in {"false", "0", "closed", "close"}:
        return {"state": "closed", "label": "Lukket", "tone": "ok"}
    return {"state": "unknown", "label": "Ukjent", "tone": "unknown"}


def door_state_bool(row: Optional[dict[str, Any]]) -> Optional[bool]:
    state = door_state_info(row).get("state")
    if state == "open":
        return True
    if state == "closed":
        return False
    return None


def relative_time_label(value: Any, now: Optional[datetime] = None) -> str:
    if not isinstance(value, datetime):
        return "-"
    now = now or local_now()
    seconds = max(0, int((now - value).total_seconds()))
    if seconds < 60:
        return "nå nettopp"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min siden"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} t siden"
    days = hours // 24
    return "1 dag siden" if days == 1 else f"{days} dager siden"


def datetime_sort_value(value: Any) -> float:
    if not isinstance(value, datetime):
        return -1.0
    if value.tzinfo is None:
        value = value.replace(tzinfo=LOCAL_TZ)
    return value.timestamp()


def door_status_payload(config: dict[str, Any], row: Optional[dict[str, Any]], now: datetime) -> dict[str, Any]:
    state = door_state_info(row)
    timestamp = row.get("timestamp") if row else None
    state_label = state["label"]
    if config.get("group_key") == "solrom":
        if state["state"] == "open":
            state_label = "Ledig"
        elif state["state"] == "closed":
            state_label = "I bruk"
    return {
        "device_id": config.get("device_id"),
        "device_key": config["device_key"],
        "title": config["title"],
        "section_title": config.get("section_title", ""),
        "group_key": config.get("group_key", ""),
        "state": state["state"],
        "state_label": state_label,
        "tone": state["tone"],
        "timestamp": timestamp,
        "last_changed": display_stamp(timestamp),
        "age_label": relative_time_label(timestamp, now),
        "event_id": row.get("id") if row else None,
        "battery_level": row.get("battery_level") if row else None,
        "device_name": row.get("device_name") if row else "",
    }


def door_change_rows(rows_desc: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(reversed(stabilized_door_change_rows(list(reversed(rows_desc)))))


def door_row_key(row: dict[str, Any]) -> str:
    if row.get("device_id") is not None:
        return f"id:{row['device_id']}"
    return f"key:{row.get('device_key') or 'unknown'}"


def stabilized_door_change_rows(rows_ascending: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes_by_device: dict[str, list[dict[str, Any]]] = {}
    last_state_by_device: dict[str, bool] = {}
    for row in rows_ascending:
        state = door_state_bool(row)
        if state is None:
            continue
        key = door_row_key(row)
        if key not in last_state_by_device or last_state_by_device[key] != state:
            changes_by_device.setdefault(key, []).append(row)
            last_state_by_device[key] = state

    stabilized: list[dict[str, Any]] = []
    for device_rows in changes_by_device.values():
        cluster: list[dict[str, Any]] = []

        def flush_cluster() -> None:
            if not cluster:
                return
            final_state = door_state_bool(cluster[-1])
            stabilized.append(next((item for item in cluster if door_state_bool(item) == final_state), cluster[-1]))

        for row in device_rows:
            if cluster:
                previous_at = cluster[-1].get("timestamp")
                current_at = row.get("timestamp")
                gap_seconds = (current_at - previous_at).total_seconds() if isinstance(previous_at, datetime) and isinstance(current_at, datetime) else None
                if gap_seconds is None or gap_seconds > HC3_DOOR_DEBOUNCE_SECONDS:
                    flush_cluster()
                    cluster = []
            cluster.append(row)
        flush_cluster()

    stabilized.sort(key=lambda row: (datetime_sort_value(row.get("timestamp")), int(row.get("id") or 0)))
    changes: list[dict[str, Any]] = []
    last_stable_state: dict[str, bool] = {}
    for row in stabilized:
        state = door_state_bool(row)
        key = door_row_key(row)
        if state is not None and last_stable_state.get(key) != state:
            changes.append(row)
            last_stable_state[key] = state
    return changes


async def door_statuses_for(
    configs: list[dict[str, Any]],
    device_ids: list[int],
    device_keys: list[str],
) -> list[dict[str, Any]]:
    now = local_now()
    if not SOURCE_MODE:
        return []
    rows = await many_mappings(
        """
        select id, timestamp, event_type, action, device_key, device_id, device_name,
               source, raw_value, state, previous_state, battery_level, extra
        from door_events
        where device_id = any(:device_ids) or device_key = any(:device_keys)
        order by timestamp desc, id desc
        limit 600
        """,
        {"device_ids": device_ids, "device_keys": device_keys},
    )
    statuses = []
    for config in sorted(configs, key=lambda item: int(item.get("sort_order") or 0)):
        latest_row = next((row for row in rows if door_config_match(row, config)), None)
        statuses.append(door_status_payload(config, latest_row, now))
    return statuses


async def door_events_for(device_key: str, configs_by_key: dict[str, dict[str, Any]], limit: int = 80) -> list[dict[str, Any]]:
    config = configs_by_key.get(device_key)
    if not config or not SOURCE_MODE:
        return []
    rows = await many_mappings(
        """
        select id, timestamp, event_type, action, device_key, device_id, device_name,
               source, raw_value, state, previous_state, battery_level, extra
        from door_events
        where device_id = :device_id or device_key = :device_key
        order by timestamp desc, id desc
        limit :limit
        """,
        {
            "device_id": config.get("device_id"),
            "device_key": config.get("device_key"),
            "limit": max(limit * 4, limit),
        },
    )
    return door_change_rows(rows)[:limit]


async def solroom_door_statuses() -> list[dict[str, Any]]:
    return await door_statuses_for(SOLROOM_DOOR_CONFIG, SOLROOM_DOOR_DEVICE_IDS, SOLROOM_DOOR_KEYS)


def solroom_room_id_from_config(config: dict[str, Any]) -> str:
    if config.get("room_id"):
        return str(config["room_id"])
    match = re.search(r"(\d+)$", str(config.get("device_key") or config.get("title") or ""))
    if not match:
        return ""
    return f"rom-{int(match.group(1)):02d}"


def normalize_solroom_room_id(value: Any) -> str:
    text_value = str(value or "").strip().lower()
    match = re.search(r"(\d+)", text_value)
    if not match:
        return ""
    return f"rom-{int(match.group(1)):02d}"


def solroom_session_room_id(row: dict[str, Any]) -> str:
    bed_id = str(row.get("sun2_bed_id") or "").strip()
    if bed_id:
        config = next((item for item in SOLROOM_DOOR_CONFIG if str(item.get("sun2_bed_id") or "") == bed_id), None)
        if config:
            return str(config.get("room_id") or "")
    return normalize_solroom_room_id(row.get("room_id") or row.get("room") or row.get("source_room_name"))


def sun_session_end_at(row: dict[str, Any]) -> Optional[datetime]:
    started_at = row.get("started_at")
    if not isinstance(started_at, datetime):
        return row.get("ended_at") if isinstance(row.get("ended_at"), datetime) else None
    try:
        duration = float(row.get("duration_minutes"))
    except (TypeError, ValueError):
        ended_at = row.get("ended_at")
        return ended_at if isinstance(ended_at, datetime) else None
    return started_at + timedelta(minutes=SUNROOM_DOOR_PAYMENT_DELAY_MINUTES + duration)


def sun_session_expected_exit_at(row: dict[str, Any]) -> Optional[datetime]:
    end_at = sun_session_end_at(row)
    if not end_at:
        return None
    return end_at + timedelta(minutes=SUNROOM_DOOR_EXIT_GRACE_MINUTES)


def solroom_session_matches_closed_status(row: dict[str, Any], closed_since: Optional[datetime], now: datetime) -> bool:
    started_at = row.get("started_at")
    expected_exit = sun_session_expected_exit_at(row)
    if not isinstance(started_at, datetime) or not isinstance(closed_since, datetime):
        return False
    if started_at > now + timedelta(minutes=SUNROOM_DOOR_SESSION_GRACE_MINUTES):
        return False
    if expected_exit and expected_exit >= closed_since - timedelta(minutes=SUNROOM_DOOR_PAYMENT_DELAY_MINUTES + 2):
        return True
    return closed_since - timedelta(minutes=30) <= started_at <= closed_since + timedelta(hours=2)


async def solroom_door_alarm_statuses(statuses: list[dict[str, Any]]) -> dict[str, Any]:
    now = local_now()
    room_by_key = {str(config.get("device_key")): solroom_room_id_from_config(config) for config in SOLROOM_DOOR_CONFIG}
    room_ids = sorted({room_id for room_id in room_by_key.values() if room_id})
    sessions_by_room = {room_id: [] for room_id in room_ids}
    if SOURCE_MODE and room_ids:
        rows = await many_mappings(
            """
            select id, room_id, room, source_room_name, sun2_bed_id, started_at, ended_at, duration_minutes
            from sun2_tanning_sessions
            where started_at >= :cutoff
            order by started_at desc, id desc
            """,
            {"cutoff": now - timedelta(hours=12)},
        )
        for row in rows:
            room_id = solroom_session_room_id(row)
            if room_id in sessions_by_room:
                sessions_by_room[room_id].append(row)

    items: list[dict[str, Any]] = []
    for status in statuses:
        room_id = room_by_key.get(str(status.get("device_key") or ""), "")
        closed_since = status.get("timestamp") if status.get("state") == "closed" else None
        duration_seconds = int((now - closed_since).total_seconds()) if isinstance(closed_since, datetime) else None
        session = None
        if status.get("state") == "closed":
            session = next(
                (
                    row
                    for row in sessions_by_room.get(room_id, [])
                    if solroom_session_matches_closed_status(row, closed_since, now)
                ),
                None,
            )
        missing_session = bool(
            status.get("state") == "closed"
            and session is None
            and duration_seconds is not None
            and duration_seconds >= int(SUNROOM_DOOR_SESSION_GRACE_MINUTES * 60)
        )
        alarm_active = bool(
            missing_session
            and duration_seconds is not None
            and duration_seconds >= int(SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES * 60)
        )
        items.append(
            {
                **status,
                "room_id": room_id,
                "session": session,
                "missing_session": missing_session,
                "alarm_active": alarm_active,
                "duration_seconds": duration_seconds,
                "duration_label": relative_time_label(closed_since, now) if isinstance(closed_since, datetime) else "-",
                "expected_exit_at": sun_session_expected_exit_at(session) if session else None,
            }
        )
    alarms = [item for item in items if item.get("alarm_active")]
    watch = [item for item in items if item.get("missing_session") and not item.get("alarm_active")]
    return {
        "generated_at": now,
        "items": items,
        "alarms": alarms,
        "watch": watch,
        "summary": {
            "alarms": len(alarms),
            "watch": len(watch),
            "busy": sum(1 for item in items if item.get("state") == "closed"),
            "rooms": len(items),
        },
        "subscribe_url": ntfy_subscribe_url(NTFY_DOORS_TOPIC, "SUN2 dørvarsler"),
        "topic_url": ntfy_topic_url(NTFY_DOORS_TOPIC),
        "threshold_minutes": SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES,
    }


def compact_duration_label(seconds: Any) -> str:
    try:
        seconds_value = max(0, int(seconds))
    except (TypeError, ValueError):
        return "-"
    if seconds_value < 60:
        return f"{seconds_value} sek"
    minutes = seconds_value // 60
    if minutes < 60:
        return f"{minutes} min"
    hours, rest = divmod(minutes, 60)
    return f"{hours} t {rest} min" if rest else f"{hours} t"


def solroom_closed_periods(rows_ascending: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    closed_by_device: dict[str, dict[str, Any]] = {}
    periods: list[dict[str, Any]] = []
    for row in stabilized_door_change_rows(rows_ascending):
        state = door_state_bool(row)
        key = door_row_key(row)
        if state is False:
            closed_by_device[key] = row
        elif state is True:
            closed_row = closed_by_device.pop(key, None)
            if closed_row:
                closed_at = closed_row.get("timestamp")
                opened_at = row.get("timestamp")
                periods.append(
                    {
                        "id": f"{key}-{closed_row.get('id')}",
                        "device_key": closed_row.get("device_key"),
                        "device_id": closed_row.get("device_id"),
                        "closed_at": closed_at,
                        "opened_at": opened_at,
                        "duration_seconds": int((opened_at - closed_at).total_seconds())
                        if isinstance(closed_at, datetime) and isinstance(opened_at, datetime)
                        else None,
                    }
                )
    for key, closed_row in closed_by_device.items():
        closed_at = closed_row.get("timestamp")
        periods.append(
            {
                "id": f"{key}-{closed_row.get('id')}",
                "device_key": closed_row.get("device_key"),
                "device_id": closed_row.get("device_id"),
                "closed_at": closed_at,
                "opened_at": None,
                "duration_seconds": int((now - closed_at).total_seconds()) if isinstance(closed_at, datetime) else None,
            }
        )
    return sorted(periods, key=lambda item: datetime_sort_value(item.get("closed_at")), reverse=True)


def solroom_session_matches_period(
    row: dict[str, Any],
    closed_at: Optional[datetime],
    opened_at: Optional[datetime],
    now: datetime,
) -> bool:
    started_at = row.get("started_at")
    if not isinstance(started_at, datetime) or not isinstance(closed_at, datetime):
        return False
    period_end = opened_at or now
    if closed_at - timedelta(minutes=15) <= started_at <= period_end + timedelta(minutes=15):
        return True
    expected_exit = sun_session_expected_exit_at(row)
    return bool(
        expected_exit
        and expected_exit >= closed_at - timedelta(minutes=SUNROOM_DOOR_PAYMENT_DELAY_MINUTES + 2)
        and started_at <= period_end + timedelta(minutes=15)
    )


def solroom_session_period_score(
    row: dict[str, Any],
    closed_at: datetime,
    opened_at: Optional[datetime],
    now: datetime,
) -> float:
    started_at = row.get("started_at")
    if not isinstance(started_at, datetime):
        return float("inf")
    period_end = opened_at or now
    start_score = abs((started_at - closed_at).total_seconds())
    expected_exit = sun_session_expected_exit_at(row)
    if isinstance(expected_exit, datetime):
        return min(start_score, abs((expected_exit - period_end).total_seconds()) + 60)
    return start_score


def solroom_match_session_for_period(
    sessions: list[dict[str, Any]],
    closed_at: Optional[datetime],
    opened_at: Optional[datetime],
    now: datetime,
) -> Optional[dict[str, Any]]:
    if not isinstance(closed_at, datetime):
        return None
    candidates = [row for row in sessions if solroom_session_matches_period(row, closed_at, opened_at, now)]
    if not candidates:
        return None
    return min(candidates, key=lambda row: solroom_session_period_score(row, closed_at, opened_at, now))


def solroom_alarm_for_period(
    alarms: list[dict[str, Any]],
    config: dict[str, Any],
    period: dict[str, Any],
    session: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    closed_at = period.get("closed_at")
    source_session_id = str((session or {}).get("source_session_id") or "")
    for alarm in alarms:
        same_device = (
            str(alarm.get("device_key") or "") == str(config.get("device_key") or "")
            or alarm.get("device_id") == config.get("device_id")
        )
        if not same_device:
            continue
        alarm_closed_at = alarm.get("door_changed_at")
        if isinstance(alarm_closed_at, datetime) and isinstance(closed_at, datetime):
            if abs((alarm_closed_at - closed_at).total_seconds()) <= HC3_DOOR_DEBOUNCE_SECONDS:
                return alarm
        if source_session_id and source_session_id == str(alarm.get("source_session_id") or ""):
            return alarm
    return None


def solroom_control_row(
    config: dict[str, Any],
    period: dict[str, Any],
    session: Optional[dict[str, Any]],
    alarm: Optional[dict[str, Any]],
    now: datetime,
) -> dict[str, Any]:
    closed_at = period.get("closed_at")
    opened_at = period.get("opened_at")
    duration_seconds = period.get("duration_seconds")
    expected_exit = sun_session_expected_exit_at(session) if session else None
    severity = "ok"
    status = "OK"
    deviation = "Ingen avvik"
    missing_session = session is None and int(duration_seconds or 0) >= int(SUNROOM_DOOR_SESSION_GRACE_MINUTES * 60)
    if alarm and alarm.get("outcome") == "false_positive":
        severity, status, deviation = "warning", "Feilalarm", "Bekreftet feilalarm"
    elif alarm and alarm.get("alarm_type") == "closed_without_session":
        severity, status, deviation = "alert", "Alarm", "Lukket uten funnet soltime"
    elif alarm:
        severity, status, deviation = "alert", "Alarm", "Alarmgrense etter solslutt"
    elif missing_session:
        severity, status, deviation = "warning", "Avvik", "Dørperiode uten Sun2-time"
    elif session:
        session_end = sun_session_end_at(session)
        compare_at = opened_at or now
        after_end_seconds = (compare_at - session_end).total_seconds() if isinstance(session_end, datetime) else 0
        if after_end_seconds >= SUNROOM_DOOR_ALERT_AFTER_END_MINUTES * 60:
            severity, status, deviation = "alert", "Alarm", "Alarmgrense etter solslutt"
        elif after_end_seconds >= SUNROOM_DOOR_WARN_AFTER_END_MINUTES * 60:
            severity, status, deviation = "warning", "Avvik", "Sen utgang"
        elif opened_at is None:
            severity, status, deviation = "active", "Pågår", "Innenfor forventet tid"
    else:
        severity, status, deviation = "waiting", "Avventer", "Kort periode uten sikker kobling"

    exit_delta_minutes = None
    if isinstance(opened_at, datetime) and isinstance(expected_exit, datetime):
        exit_delta_minutes = (opened_at - expected_exit).total_seconds() / 60
    session_end = sun_session_end_at(session) if session else None
    return {
        "id": period.get("id"),
        "title": config.get("title"),
        "room_id": config.get("room_id"),
        "device_key": config.get("device_key"),
        "closed_at": closed_at,
        "opened_at": opened_at,
        "duration_seconds": duration_seconds,
        "duration_label": compact_duration_label(duration_seconds),
        "session": {
            "id": session.get("id"),
            "source_session_id": session.get("source_session_id"),
            "started_at": session.get("started_at"),
            "ended_at": session_end,
            "expected_exit_at": expected_exit,
            "duration_minutes": session.get("duration_minutes"),
            "sun2_bed_id": session.get("sun2_bed_id"),
        } if session else None,
        "expected_exit_at": expected_exit,
        "exit_delta_minutes": exit_delta_minutes,
        "severity": severity,
        "status": status,
        "deviation": deviation,
        "missing_session": missing_session,
        "alarm": alarm,
    }


async def solroom_door_day_control() -> dict[str, Any]:
    now = local_now()
    day_start, day_end = day_bounds(now.date())
    device_ids = [int(item["device_id"]) for item in SOLROOM_DOOR_CONFIG if item.get("device_id") is not None]
    device_keys = [str(item["device_key"]) for item in SOLROOM_DOOR_CONFIG]
    door_rows = await many_mappings(
        """
        select id, timestamp, action, device_key, device_id, raw_value, state
        from door_events
        where (device_id = any(:device_ids) or device_key = any(:device_keys))
          and timestamp >= :start and timestamp < :end
        order by timestamp asc, id asc
        """,
        {"device_ids": device_ids, "device_keys": device_keys, "start": day_start - timedelta(hours=12), "end": day_end},
    )
    sessions = await many_mappings(
        """
        select id, source_session_id, room_id, room, source_room_name, sun2_bed_id,
               started_at, ended_at, duration_minutes
        from sun2_tanning_sessions
        where started_at >= :start and started_at < :end
        order by started_at desc, id desc
        """,
        {"start": day_start - timedelta(hours=2), "end": day_end + timedelta(hours=2)},
    )
    alarms = await many_mappings(
        """
        select id, alarm_type, status, outcome, title, device_key, device_id, room_id,
               sun2_bed_id, source_session_id, door_changed_at, expected_exit_at,
               detected_at, resolved_at, notification_status, last_notification_at
        from alarm_events
        where domain = 'doors'
          and ((detected_at >= :start and detected_at < :end)
               or (door_changed_at >= :start and door_changed_at < :end))
        order by detected_at desc, id desc
        """,
        {"start": day_start, "end": day_end},
    )

    sessions_by_room: dict[str, list[dict[str, Any]]] = {}
    for session in sessions:
        room_id = solroom_session_room_id(session)
        if room_id:
            sessions_by_room.setdefault(room_id, []).append(session)

    periods_by_device: dict[str, list[dict[str, Any]]] = {}
    for period in solroom_closed_periods(door_rows, now):
        closed_at = period.get("closed_at")
        opened_at = period.get("opened_at")
        if isinstance(closed_at, datetime) and closed_at >= day_end:
            continue
        if isinstance(opened_at, datetime) and opened_at < day_start and (not isinstance(closed_at, datetime) or closed_at < day_start):
            continue
        periods_by_device.setdefault(door_row_key(period), []).append(period)

    rows: list[dict[str, Any]] = []
    matched_session_ids: set[int] = set()
    for config in SOLROOM_DOOR_CONFIG:
        room_sessions = sessions_by_room.get(str(config.get("room_id") or ""), [])
        device_periods = periods_by_device.get(
            f"id:{config['device_id']}" if config.get("device_id") is not None else f"key:{config['device_key']}",
            [],
        )
        for period in device_periods:
            session = solroom_match_session_for_period(room_sessions, period.get("closed_at"), period.get("opened_at"), now)
            if session and session.get("id") is not None:
                matched_session_ids.add(int(session["id"]))
            alarm = solroom_alarm_for_period(alarms, config, period, session)
            rows.append(solroom_control_row(config, period, session, alarm, now))

        for session in room_sessions:
            started_at = session.get("started_at")
            if not isinstance(started_at, datetime) or not day_start <= started_at < day_end:
                continue
            if session.get("id") is not None and int(session["id"]) in matched_session_ids:
                continue
            alarm = next(
                (
                    item for item in alarms
                    if item.get("source_session_id")
                    and item.get("source_session_id") == session.get("source_session_id")
                ),
                None,
            )
            rows.append(
                {
                    "id": f"session-{session.get('id')}",
                    "title": config.get("title"),
                    "room_id": config.get("room_id"),
                    "device_key": config.get("device_key"),
                    "closed_at": None,
                    "opened_at": None,
                    "duration_seconds": None,
                    "duration_label": "-",
                    "session": {
                        "id": session.get("id"),
                        "source_session_id": session.get("source_session_id"),
                        "started_at": started_at,
                        "ended_at": sun_session_end_at(session),
                        "expected_exit_at": sun_session_expected_exit_at(session),
                        "duration_minutes": session.get("duration_minutes"),
                        "sun2_bed_id": session.get("sun2_bed_id"),
                    },
                    "expected_exit_at": sun_session_expected_exit_at(session),
                    "exit_delta_minutes": None,
                    "severity": "alert" if alarm else "warning",
                    "status": "Alarm" if alarm else "Avvik",
                    "deviation": "Sun2-time uten funnet dørperiode",
                    "missing_session": False,
                    "alarm": alarm,
                }
            )

    rows.sort(
        key=lambda item: datetime_sort_value(item.get("closed_at") or (item.get("session") or {}).get("started_at")),
        reverse=True,
    )
    return {
        "generated_at": now,
        "rows": rows,
        "summary": {
            "rows": len(rows),
            "deviations": sum(1 for item in rows if item.get("severity") in {"warning", "alert"}),
            "alarms": sum(1 for item in rows if item.get("alarm") or item.get("severity") == "alert"),
            "missing": sum(1 for item in rows if not item.get("session") or not item.get("closed_at")),
        },
    }


async def solroom_door_events(device_key: str, limit: int = 80) -> list[dict[str, Any]]:
    return await door_events_for(device_key, SOLROOM_DOOR_BY_KEY, limit)


async def other_door_statuses() -> list[dict[str, Any]]:
    return await door_statuses_for(OTHER_DOOR_CONFIG, OTHER_DOOR_DEVICE_IDS, OTHER_DOOR_KEYS)


async def other_door_events(device_key: str, limit: int = 80) -> list[dict[str, Any]]:
    return await door_events_for(device_key, OTHER_DOOR_BY_KEY, limit)


def amount_sum(*values: Any) -> float:
    total = 0.0
    for value in values:
        try:
            total += float(value or 0)
        except (TypeError, ValueError):
            pass
    return total


def normalize_week_start(value: Optional[str], fallback: date) -> date:
    try:
        parsed = date.fromisoformat((value or "").strip())
    except ValueError:
        parsed = fallback
    return parsed - timedelta(days=parsed.weekday())


def date_key(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


async def revenue_week_data(week_start: date) -> list[dict[str, Any]]:
    week_end = week_start + timedelta(days=7)
    week_start_dt = datetime.combine(week_start, datetime.min.time())
    week_end_dt = datetime.combine(week_end, datetime.min.time())
    sol_rows = await many_mappings(
        """
        select stat_date as day,
               count(*) as count,
               coalesce(sum(paid_amount_kr), 0) as amount
        from sun2_tanning_sessions
        where stat_date >= :start and stat_date < :end
        group by stat_date
        """,
        {"start": week_start, "end": week_end},
    )
    parking_rows = await many_mappings(
        """
        select start_time::date as day,
               count(*) as count,
               coalesce(sum(fee_inc_vat), 0) as amount
        from parkering
        where start_time >= :start and start_time < :end
        group by start_time::date
        """,
        {"start": week_start_dt, "end": week_end_dt},
    )
    sol_by_day = {date_key(row.get("day")): float(row.get("amount") or 0) for row in sol_rows}
    sol_count_by_day = {date_key(row.get("day")): int(row.get("count") or 0) for row in sol_rows}
    parking_by_day = {date_key(row.get("day")): float(row.get("amount") or 0) for row in parking_rows}
    parking_count_by_day = {date_key(row.get("day")): int(row.get("count") or 0) for row in parking_rows}
    return [
        {
            "day": week_start + timedelta(days=offset),
            "sol": sol_by_day.get(week_start + timedelta(days=offset), 0.0),
            "sol_count": sol_count_by_day.get(week_start + timedelta(days=offset), 0),
            "parking": parking_by_day.get(week_start + timedelta(days=offset), 0.0),
            "parking_count": parking_count_by_day.get(week_start + timedelta(days=offset), 0),
        }
        for offset in range(7)
    ]


def money_compare_short(current: Any, previous: Any, label: str) -> str:
    try:
        current_f = float(current or 0)
        previous_f = float(previous or 0)
    except (TypeError, ValueError):
        return "-"
    diff = current_f - previous_f
    if round(diff) == 0:
        return f"Lik mot {label}"
    sign = "+" if diff > 0 else "-"
    return f"{sign}{fmt_money(abs(diff))} mot {label}"


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if SNAPSHOT_MODE:
        if path in PUBLIC_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES) or path == "/api/snapshot/ingest":
            return await call_next(request)
        if PUBLIC_DASHBOARD_PUBLIC or valid_snapshot_session(request):
            request.state.access_key = public_access_key()
            return await call_next(request)
        if wants_html(request):
            return RedirectResponse("/auth/login", status_code=303)
        return JSONResponse({"detail": "Ugyldig eller manglende innlogging"}, status_code=401)

    if path in PUBLIC_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES):
        return await call_next(request)
    username, password = presented_credentials(request)
    access_key = await find_access_key(username, password)
    if not access_key:
        await log_access_attempt(request, False, "online_missing_or_invalid_key", attempted_username=username)
        if wants_html(request):
            return RedirectResponse("/auth/login", status_code=303)
        return JSONResponse({"detail": "Ugyldig eller manglende innlogging"}, status_code=401)
    request.state.access_key = access_key
    if await should_log_online_activity(request, access_key):
        await log_access_attempt(request, True, "online_dashboard", access_key)
    else:
        await touch_access_key(access_key, request)
    return await call_next(request)


async def one_mapping(query: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    async with async_session() as session:
        row = (await session.execute(text(query), params or {})).mappings().first()
    return dict(row) if row else {}


async def many_mappings(query: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    async with async_session() as session:
        rows = (await session.execute(text(query), params or {})).mappings().all()
    return [dict(row) for row in rows]


async def source_dashboard_data() -> dict[str, Any]:
    now = local_now()
    today = now.date()
    yesterday = today - timedelta(days=1)
    last_week_same_day = today - timedelta(days=7)
    two_weeks_same_day = today - timedelta(days=14)
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    previous_week_start = week_start - timedelta(days=7)
    previous_week_end = week_start
    previous_month_end = month_start
    previous_month_start = (month_start - timedelta(days=1)).replace(day=1)
    start, end = day_bounds(today)
    yesterday_start, yesterday_end = day_bounds(yesterday)
    last_week_same_day_start, last_week_same_day_end = day_bounds(last_week_same_day)
    two_weeks_same_day_start, two_weeks_same_day_end = day_bounds(two_weeks_same_day)
    week_start_dt = datetime.combine(week_start, datetime.min.time())
    previous_week_start_dt = datetime.combine(previous_week_start, datetime.min.time())
    previous_week_end_dt = datetime.combine(previous_week_end, datetime.min.time())
    month_start_dt = datetime.combine(month_start, datetime.min.time())
    previous_month_start_dt = datetime.combine(previous_month_start, datetime.min.time())
    previous_month_end_dt = datetime.combine(previous_month_end, datetime.min.time())

    soling = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(duration_minutes), 0) as minutes,
               coalesce(sum(paid_amount_kr), 0) as amount,
               max(imported_at) as updated_at
        from sun2_tanning_sessions
        where stat_date = :today
        """,
        {"today": today},
    )
    soling_yesterday = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(duration_minutes), 0) as minutes,
               coalesce(sum(paid_amount_kr), 0) as amount
        from sun2_tanning_sessions
        where stat_date = :day
        """,
        {"day": yesterday},
    )
    soling_last_week_same_day = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(duration_minutes), 0) as minutes,
               coalesce(sum(paid_amount_kr), 0) as amount
        from sun2_tanning_sessions
        where stat_date = :day
        """,
        {"day": last_week_same_day},
    )
    soling_two_weeks_same_day = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(duration_minutes), 0) as minutes,
               coalesce(sum(paid_amount_kr), 0) as amount
        from sun2_tanning_sessions
        where stat_date = :day
        """,
        {"day": two_weeks_same_day},
    )
    soling_week = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(duration_minutes), 0) as minutes,
               coalesce(sum(paid_amount_kr), 0) as amount
        from sun2_tanning_sessions
        where stat_date >= :start and stat_date <= :today
        """,
        {"start": week_start, "today": today},
    )
    soling_previous_week = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(duration_minutes), 0) as minutes,
               coalesce(sum(paid_amount_kr), 0) as amount
        from sun2_tanning_sessions
        where stat_date >= :start and stat_date < :end
        """,
        {"start": previous_week_start, "end": previous_week_end},
    )
    soling_month = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(duration_minutes), 0) as minutes,
               coalesce(sum(paid_amount_kr), 0) as amount
        from sun2_tanning_sessions
        where stat_date >= :start and stat_date <= :today
        """,
        {"start": month_start, "today": today},
    )
    soling_previous_month = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(duration_minutes), 0) as minutes,
               coalesce(sum(paid_amount_kr), 0) as amount
        from sun2_tanning_sessions
        where stat_date >= :start and stat_date < :end
        """,
        {"start": previous_month_start, "end": previous_month_end},
    )
    latest_soling = await one_mapping(
        """
        select started_at, room
        from sun2_tanning_sessions
        where stat_date = :today
        order by started_at desc
        limit 1
        """,
        {"today": today},
    )
    session_import = await one_mapping(
        """
        select last_success_at as updated_at,
               last_failed_at
        from import_job_status
        where job_name = 'sun2_sessions_import'
        limit 1
        """
    )
    if not session_import.get("updated_at"):
        session_import = await one_mapping(
            """
            select max(timestamp) as updated_at
            from sun2_session_import_runs
            where ok = true
            """
        )
    soling_reference_at = session_import.get("updated_at")
    if not isinstance(soling_reference_at, datetime):
        soling_reference_at = soling.get("updated_at")
    if not isinstance(soling_reference_at, datetime):
        soling_reference_at = now
    last_week_soling_same_time_end = datetime.combine(last_week_same_day, soling_reference_at.time())
    soling_last_week_same_time = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(duration_minutes), 0) as minutes,
               coalesce(sum(paid_amount_kr), 0) as amount
        from sun2_tanning_sessions
        where started_at >= :start and started_at < :end
        """,
        {"start": last_week_same_day_start, "end": last_week_soling_same_time_end},
    )
    parking_import = await one_mapping(
        """
        select last_success_at as updated_at,
               last_failed_at
        from import_job_status
        where job_name = 'easypark_parking_import'
        limit 1
        """
    )
    parking_reference_at = parking_import.get("updated_at")
    if not isinstance(parking_reference_at, datetime):
        parking_reference_at = now
    last_week_same_time_end = datetime.combine(last_week_same_day, parking_reference_at.time())
    parking = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(fee_inc_vat), 0) as amount,
               count(*) filter (where lower(coalesce(status, '')) <> 'ended') as active_count,
               max(imported_at) as updated_at
        from parkering
        where start_time >= :start and start_time < :end
        """,
        {"start": start, "end": end},
    )
    parking_yesterday = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(fee_inc_vat), 0) as amount
        from parkering
        where start_time >= :start and start_time < :end
        """,
        {"start": yesterday_start, "end": yesterday_end},
    )
    parking_last_week_same_day = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(fee_inc_vat), 0) as amount
        from parkering
        where start_time >= :start and start_time < :end
        """,
        {"start": last_week_same_day_start, "end": last_week_same_day_end},
    )
    parking_last_week_same_time = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(fee_inc_vat), 0) as amount
        from parkering
        where start_time >= :start and start_time < :end
        """,
        {"start": last_week_same_day_start, "end": last_week_same_time_end},
    )
    parking_two_weeks_same_day = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(fee_inc_vat), 0) as amount
        from parkering
        where start_time >= :start and start_time < :end
        """,
        {"start": two_weeks_same_day_start, "end": two_weeks_same_day_end},
    )
    parking_week = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(fee_inc_vat), 0) as amount
        from parkering
        where start_time >= :start and start_time < :end
        """,
        {"start": week_start_dt, "end": end},
    )
    parking_previous_week = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(fee_inc_vat), 0) as amount
        from parkering
        where start_time >= :start and start_time < :end
        """,
        {"start": previous_week_start_dt, "end": previous_week_end_dt},
    )
    parking_month = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(fee_inc_vat), 0) as amount
        from parkering
        where start_time >= :start and start_time < :end
        """,
        {"start": month_start_dt, "end": end},
    )
    parking_previous_month = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(fee_inc_vat), 0) as amount
        from parkering
        where start_time >= :start and start_time < :end
        """,
        {"start": previous_month_start_dt, "end": previous_month_end_dt},
    )
    latest_parking = await one_mapping(
        """
        select start_time, car_license_number
        from parkering
        where start_time >= :start and start_time < :end
        order by start_time desc
        limit 1
        """,
        {"start": start, "end": end},
    )
    lights = await one_mapping(
        """
        select timestamp, bucket_start, lux,
               light_lyslist, light_reklame, light_spot_inngang, light_parkering
        from utelys_samples
        order by bucket_start desc
        limit 1
        """
    )
    vent = await one_mapping(
        """
        select timestamp, bucket_start, mode,
               temp_1etg, temp_2etg, temp_vip, temp_avg_inne,
               temp_ute, temp_yr, temp_loft, temp_kjeller, humidity_kjeller,
               humidity_1etg, humidity_2etg, humidity_vip, humidity_ute,
               humidity_yr, humidity_loft, humidity_luftinntak,
               temp_passiv, temp_luftinntak,
               fan_vip, fan_2etg, fan_tak, fan_avfukter
        from ventilasjon_samples
        order by bucket_start desc
        limit 1
        """
    )
    energy_now = await one_mapping(
        """
        select bucket_start, timestamp, inntak_w, belysning_w, varmepumper_w, avfukter_w, differanse_beregnet_w
        from energy_fibaro_samples
        order by bucket_start desc
        limit 1
        """
    )
    energy_today = await one_mapping(
        """
        select coalesce(sum(inntak_delta_kwh), 0) as kwh,
               count(*) as samples
        from energy_fibaro_samples
        where bucket_start >= :start and bucket_start < :end
        """,
        {"start": start, "end": end},
    )
    solroom_doors = await solroom_door_statuses()
    other_doors = await other_door_statuses()
    door_alarm = await solroom_door_alarm_statuses(solroom_doors)
    door_day_control = await solroom_door_day_control()

    inside_values = [vent.get("temp_1etg"), vent.get("temp_2etg"), vent.get("temp_vip")]
    inside_values = [float(value) for value in inside_values if value is not None]
    inside_avg = vent.get("temp_avg_inne")
    if inside_avg is None and inside_values:
        inside_avg = sum(inside_values) / len(inside_values)

    outside_values = [vent.get("temp_ute"), vent.get("temp_yr")]
    outside_values = [float(value) for value in outside_values if value is not None]
    outside = sum(outside_values) / len(outside_values) if outside_values else None

    data = {
        "now": now,
        "open_state": operating_window(now),
        "soling": soling,
        "soling_yesterday": soling_yesterday,
        "soling_last_week_same_day": soling_last_week_same_day,
        "soling_last_week_same_time": soling_last_week_same_time,
        "soling_two_weeks_same_day": soling_two_weeks_same_day,
        "soling_week": soling_week,
        "soling_previous_week": soling_previous_week,
        "soling_month": soling_month,
        "soling_previous_month": soling_previous_month,
        "latest_soling": latest_soling,
        "session_import": session_import,
        "parking_import": parking_import,
        "parking": parking,
        "parking_yesterday": parking_yesterday,
        "parking_last_week_same_day": parking_last_week_same_day,
        "parking_last_week_same_time": parking_last_week_same_time,
        "parking_two_weeks_same_day": parking_two_weeks_same_day,
        "parking_week": parking_week,
        "parking_previous_week": parking_previous_week,
        "parking_month": parking_month,
        "parking_previous_month": parking_previous_month,
        "latest_parking": latest_parking,
        "lights": lights,
        "vent": vent,
        "energy_now": energy_now,
        "energy_today": energy_today,
        "inside_avg": inside_avg,
        "outside": outside,
        "outside_sensor": vent.get("temp_ute"),
        "yr_temp": vent.get("temp_yr"),
        "innluft": vent.get("temp_luftinntak") if vent.get("temp_luftinntak") is not None else vent.get("temp_passiv"),
        "light_items": [
            ("Lyslist", lights.get("light_lyslist")),
            ("Reklame", lights.get("light_reklame")),
            ("Inngang", lights.get("light_spot_inngang")),
            ("Parkering", lights.get("light_parkering")),
        ],
        "fan_items": [
            ("VIP", vent.get("fan_vip")),
            ("2.etg", vent.get("fan_2etg")),
            ("Tak/loft", vent.get("fan_tak")),
            ("Avfukter", vent.get("fan_avfukter")),
        ],
        "solroom_doors": solroom_doors,
        "other_doors": other_doors,
        "door_alarm": door_alarm,
        "door_day_control": door_day_control,
    }
    data["revenue"] = {
        "today": amount_sum(data["soling"].get("amount"), data["parking"].get("amount")),
        "yesterday": amount_sum(data["soling_yesterday"].get("amount"), data["parking_yesterday"].get("amount")),
        "last_week_same_day": amount_sum(data["soling_last_week_same_day"].get("amount"), data["parking_last_week_same_day"].get("amount")),
        "two_weeks_same_day": amount_sum(data["soling_two_weeks_same_day"].get("amount"), data["parking_two_weeks_same_day"].get("amount")),
        "week": amount_sum(data["soling_week"].get("amount"), data["parking_week"].get("amount")),
        "previous_week": amount_sum(data["soling_previous_week"].get("amount"), data["parking_previous_week"].get("amount")),
        "month": amount_sum(data["soling_month"].get("amount"), data["parking_month"].get("amount")),
        "previous_month": amount_sum(data["soling_previous_month"].get("amount"), data["parking_previous_month"].get("amount")),
    }
    data["revenue_updated_at"] = max(
        (
            stamp
            for stamp in (
                data["session_import"].get("updated_at"),
                data["soling"].get("updated_at"),
                data["parking_import"].get("updated_at"),
                data["parking"].get("updated_at"),
            )
            if isinstance(stamp, datetime)
        ),
        default=None,
    )
    return data


async def latest_snapshot_payload() -> dict[str, Any]:
    async with async_session() as session:
        row = (
            await session.execute(
                text(
                    """
                    select payload, received_at
                    from online_dashboard_snapshots
                    where name = :name
                    limit 1
                    """
                ),
                {"name": PUBLIC_DASHBOARD_SNAPSHOT_NAME},
            )
        ).mappings().first()
    if not row:
        now = local_now()
        empty = {
            "now": now,
            "open_state": operating_window(now),
            "soling": {},
            "soling_yesterday": {},
            "soling_last_week_same_day": {},
            "soling_last_week_same_time": {},
            "soling_two_weeks_same_day": {},
            "soling_week": {},
            "soling_previous_week": {},
            "soling_month": {},
            "soling_previous_month": {},
            "latest_soling": {},
            "session_import": {},
            "parking_import": {},
            "parking": {},
            "parking_yesterday": {},
            "parking_last_week_same_day": {},
            "parking_last_week_same_time": {},
            "parking_two_weeks_same_day": {},
            "parking_week": {},
            "parking_previous_week": {},
            "parking_month": {},
            "parking_previous_month": {},
            "latest_parking": {},
            "lights": {},
            "vent": {},
            "energy_now": {},
            "energy_today": {},
            "inside_avg": None,
            "outside": None,
            "outside_sensor": None,
            "yr_temp": None,
            "innluft": None,
            "light_items": [],
            "fan_items": [],
            "solroom_doors": [],
            "other_doors": [],
            "door_alarm": {
                "generated_at": now,
                "items": [],
                "alarms": [],
                "watch": [],
                "summary": {"alarms": 0, "watch": 0, "busy": 0, "rooms": 0},
                "subscribe_url": ntfy_subscribe_url(NTFY_DOORS_TOPIC, "SUN2 dørvarsler"),
                "topic_url": ntfy_topic_url(NTFY_DOORS_TOPIC),
                "threshold_minutes": SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES,
            },
            "door_day_control": {
                "generated_at": now,
                "rows": [],
                "summary": {"rows": 0, "deviations": 0, "alarms": 0, "missing": 0},
            },
            "revenue": {},
            "revenue_updated_at": None,
            "_snapshot": {"missing": True},
        }
        return empty
    payload = hydrate_value(row["payload"])
    data = payload.get("data", payload)
    now_value = local_now()
    data["now"] = now_value
    data["open_state"] = operating_window(now_value)
    data["_snapshot"] = {
        **dict(data.get("_snapshot") or {}),
        "received_at": row.get("received_at"),
    }
    return data


async def dashboard_data() -> dict[str, Any]:
    if SNAPSHOT_MODE:
        return await latest_snapshot_payload()
    return await source_dashboard_data()


async def temperature_ranges(day: date) -> dict[str, Any]:
    start, end = day_bounds(day)
    return await one_mapping(
        """
        select min(temp_avg_inne) as min_inne, max(temp_avg_inne) as max_inne,
               min(temp_ute) as min_ute, max(temp_ute) as max_ute,
               min(temp_loft) as min_loft, max(temp_loft) as max_loft
        from ventilasjon_samples
        where bucket_start >= :start and bucket_start < :end
        """,
        {"start": start, "end": end},
    )


def public_dashboard_ingest_url() -> str:
    url = PUBLIC_DASHBOARD_SYNC_URL.rstrip("/")
    if not url:
        return ""
    if not url.endswith("/api/snapshot/ingest"):
        url = f"{url}/api/snapshot/ingest"
    return url


def snapshot_change_hash(payload: dict[str, Any]) -> str:
    comparable = json.loads(canonical_json(payload))
    data = comparable.get("data") or {}
    for volatile_key in ["now", "open_state", "_snapshot"]:
        data.pop(volatile_key, None)
    comparable.pop("published_at", None)
    return hashlib.sha256(canonical_json(comparable).encode("utf-8")).hexdigest()


async def build_public_dashboard_snapshot() -> dict[str, Any]:
    source_data = await source_dashboard_data()
    now_value = local_now()
    today = source_data["now"].date()
    week_start = today - timedelta(days=today.weekday())
    public_data = json.loads(canonical_json(source_data))

    latest_parking = public_data.get("latest_parking") or {}
    public_data["latest_parking"] = {"start_time": latest_parking.get("start_time")}
    public_data["_snapshot"] = {
        "schema_version": 1,
        "published_at": now_value.isoformat(),
        "source": "qnap-fibaro10",
        "privacy": "aggregates_only",
    }
    public_data["_charts"] = {
        "revenue_week": {
            "week_start": week_start.isoformat(),
            "rows": json.loads(canonical_json(await revenue_week_data(week_start))),
        }
    }
    public_data["_ranges"] = {
        "temperature_today": json.loads(canonical_json(await temperature_ranges(today))),
    }
    return {
        "schema_version": 1,
        "name": PUBLIC_DASHBOARD_SNAPSHOT_NAME,
        "source": "qnap-fibaro10",
        "published_at": now_value.isoformat(),
        "data": public_data,
    }


def post_snapshot_sync(payload: dict[str, Any]) -> dict[str, Any]:
    url = public_dashboard_ingest_url()
    if not url:
        raise RuntimeError("PUBLIC_DASHBOARD_SYNC_URL mangler.")
    body = canonical_json(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {PUBLIC_DASHBOARD_SYNC_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=PUBLIC_DASHBOARD_SYNC_TIMEOUT_SECONDS) as response:
        response_body = response.read().decode("utf-8", errors="replace")
    return json.loads(response_body) if response_body else {"status": "ok"}


async def public_dashboard_sync_worker() -> None:
    last_hash = ""
    while True:
        try:
            payload = await build_public_dashboard_snapshot()
            payload_hash = snapshot_change_hash(payload)
            if payload_hash != last_hash:
                await asyncio.to_thread(post_snapshot_sync, payload)
                last_hash = payload_hash
        except Exception as exc:
            print(f"public dashboard sync failed: {exc}", flush=True)
        await asyncio.sleep(PUBLIC_DASHBOARD_SYNC_INTERVAL_SECONDS)


async def ensure_snapshot_table() -> None:
    async with engine.begin() as conn:
        await conn.execute(text(SNAPSHOT_TABLE_SQL))


def render_login(error: str = "") -> HTMLResponse:
    return HTMLResponse(
        LOGIN_HTML.replace("{{ error }}", error),
        status_code=401 if error else 200,
    )


@app.on_event("startup")
async def startup():
    global public_dashboard_sync_task
    if SNAPSHOT_MODE:
        await ensure_snapshot_table()
    elif PUBLIC_DASHBOARD_SYNC_ENABLED and PUBLIC_DASHBOARD_SYNC_TOKEN and public_dashboard_ingest_url():
        public_dashboard_sync_task = asyncio.create_task(public_dashboard_sync_worker())


@app.get("/health")
async def health():
    return {"ok": True, "service": "online_dashboard", "mode": ONLINE_DASHBOARD_MODE}


@app.post("/api/snapshot/ingest")
async def ingest_snapshot(request: Request):
    if not SNAPSHOT_MODE:
        return JSONResponse({"detail": "Snapshot ingest er bare aktiv i snapshot-modus."}, status_code=404)
    if not PUBLIC_DASHBOARD_INGEST_TOKEN:
        return JSONResponse({"detail": "PUBLIC_DASHBOARD_INGEST_TOKEN mangler."}, status_code=503)
    auth = request.headers.get("authorization", "")
    expected = f"Bearer {PUBLIC_DASHBOARD_INGEST_TOKEN}"
    if not hmac.compare_digest(auth, expected):
        return JSONResponse({"detail": "Ugyldig ingest-token."}, status_code=401)
    payload = await request.json()
    if not isinstance(payload, dict) or int(payload.get("schema_version") or 0) < 1 or "data" not in payload:
        return JSONResponse({"detail": "Ugyldig snapshot-payload."}, status_code=400)
    name = str(payload.get("name") or PUBLIC_DASHBOARD_SNAPSHOT_NAME).strip() or PUBLIC_DASHBOARD_SNAPSHOT_NAME
    payload_hash = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    source_published_at = payload.get("published_at")
    try:
        source_published = datetime.fromisoformat(str(source_published_at)) if source_published_at else None
    except ValueError:
        source_published = None
    async with async_session() as session:
        await session.execute(
            text(
                """
                insert into online_dashboard_snapshots
                    (name, payload, payload_hash, source_published_at, received_at)
                values
                    (:name, cast(:payload as jsonb), :payload_hash, :source_published_at, :received_at)
                on conflict (name) do update
                set payload = excluded.payload,
                    payload_hash = excluded.payload_hash,
                    source_published_at = excluded.source_published_at,
                    received_at = excluded.received_at
                """
            ),
            {
                "name": name,
                "payload": canonical_json(payload),
                "payload_hash": payload_hash,
                "source_published_at": source_published,
                "received_at": datetime.utcnow(),
            },
        )
        await session.commit()
    return {"ok": True, "name": name, "payload_hash": payload_hash}


@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse("/static/lilletorget-favicon.png", status_code=307)


@app.get("/auth/login", response_class=HTMLResponse)
async def login_view():
    return render_login()


@app.post("/auth/login")
async def login_submit(request: Request):
    form = await request.form()
    username = normalize_username(str(form.get("username") or ""))
    password = str(form.get("password") or "").strip()
    if SNAPSHOT_MODE:
        expected_user = normalize_username(PUBLIC_DASHBOARD_USERNAME)
        valid = (
            bool(expected_user)
            and bool(PUBLIC_DASHBOARD_PASSWORD)
            and username == expected_user
            and hmac.compare_digest(password, PUBLIC_DASHBOARD_PASSWORD)
        )
        if not valid:
            return render_login("Ugyldig brukernavn eller passord")
        response = RedirectResponse("/", status_code=303)
        forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
        secure_cookie = request.url.scheme == "https" or forwarded_proto == "https"
        response.set_cookie(
            SNAPSHOT_SESSION_COOKIE_NAME,
            snapshot_session_token(expected_user),
            max_age=60 * 60 * 24 * 30,
            httponly=True,
            secure=secure_cookie,
            samesite="lax",
        )
        return response

    access_key = await find_access_key(username, password)
    if not access_key:
        await log_access_attempt(request, False, "online_failed_login", attempted_username=username)
        return render_login("Ugyldig brukernavn eller passord")
    response = RedirectResponse("/", status_code=303)
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
    secure_cookie = request.url.scheme == "https" or forwarded_proto == "https"
    response.set_cookie(AUTH_USER_COOKIE_NAME, username, max_age=60 * 60 * 24 * 365, httponly=True, secure=secure_cookie, samesite="lax")
    response.set_cookie(AUTH_COOKIE_NAME, password, max_age=60 * 60 * 24 * 365, httponly=True, secure=secure_cookie, samesite="lax")
    await log_access_attempt(request, True, "online_login", access_key)
    return response


@app.post("/logg-ut")
async def logout():
    response = RedirectResponse("/auth/login", status_code=303)
    response.delete_cookie(AUTH_USER_COOKIE_NAME)
    response.delete_cookie(AUTH_COOKIE_NAME)
    response.delete_cookie(SNAPSHOT_SESSION_COOKIE_NAME)
    return response


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    data = await dashboard_data()
    user = escape(request.state.access_key["name"])
    show_revenue = can_manage(request.state.access_key)
    money = lambda value: money_if_allowed(request.state.access_key, value)
    soling_hours = float(data["soling"].get("minutes") or 0) / 60
    week_soling_hours = float(data["soling_week"].get("minutes") or 0) / 60
    latest_soling_room = escape(str(data["latest_soling"].get("room") or "").strip())
    latest_soling = "Siste soling -"
    if data["latest_soling"].get("started_at"):
        room_suffix = f" · {latest_soling_room}" if latest_soling_room else ""
        latest_soling = f"Siste {fmt_time(data['latest_soling'].get('started_at'))}{room_suffix}"
    latest_parking_plate = escape(str(data["latest_parking"].get("car_license_number") or "").strip())
    latest_parking = "Siste parkering -"
    if data["latest_parking"].get("start_time"):
        plate_suffix = f" · {latest_parking_plate}" if latest_parking_plate else ""
        latest_parking = f"Siste {fmt_time(data['latest_parking'].get('start_time'))}{plate_suffix}"
    revenue_card = ""
    if show_revenue:
        revenue_card = f"""
      <article class="metric-card accent-revenue is-wide revenue-card" data-revenue-card="1">
        <a class="card-link revenue-main-link" href="/omsetning" aria-label="Apne omsetning">
        <div class="metric-head"><span>Omsetning</span>{metric_icon("revenue")}</div>
        <strong>{fmt_money(data["revenue"].get("today"))}<em>/{fmt_money(data["revenue"].get("yesterday"))}</em></strong>
        <small>I dag / i går - sol {fmt_money(data["soling"].get("amount"))} - park {fmt_money(data["parking"].get("amount"))}</small>
        <small class="updated-line">Oppdatert {fmt_time(data["revenue_updated_at"])}</small>
        </a>
        <a class="revenue-chart-link" href="/omsetning/uke" aria-label="Apne omsetningsdiagram">{metric_icon("chart")}</a>
      </article>
        """
    html = DASHBOARD_HTML
    replacements = {
        "{{ user }}": user,
        "{{ now }}": data["now"].strftime("%d.%m.%Y %H:%M"),
        "{{ open_label }}": data["open_state"]["label"],
        "{{ open_detail }}": data["open_state"]["detail"],
        "{{ open_progress }}": str(data["open_state"]["progress"]),
        "{{ sun_icon }}": metric_icon("sun"),
        "{{ soling_count }}": fmt_int(data["soling"].get("count")),
        "{{ soling_yesterday_count }}": fmt_int(data["soling_yesterday"].get("count")),
        "{{ soling_amount }}": money(data["soling"].get("amount")),
        "{{ soling_minutes }}": f"{soling_hours:.1f} t".replace(".", ","),
        "{{ soling_compare }}": compare_text(data["soling"].get("count"), data["soling_yesterday"].get("count"), " stk"),
        "{{ soling_week_count }}": fmt_int(data["soling_week"].get("count")),
        "{{ soling_week_amount }}": money(data["soling_week"].get("amount")),
        "{{ soling_week_minutes }}": f"{week_soling_hours:.1f} t".replace(".", ","),
        "{{ soling_month_count }}": fmt_int(data["soling_month"].get("count")),
        "{{ soling_month_amount }}": money(data["soling_month"].get("amount")),
        "{{ latest_soling }}": latest_soling,
        "{{ soling_time }}": fmt_time(data["session_import"].get("updated_at")) if data["session_import"].get("updated_at") else fmt_time(data["soling"].get("updated_at")),
        "{{ parking_icon }}": metric_icon("parking"),
        "{{ parking_count }}": fmt_int(data["parking"].get("count")),
        "{{ parking_yesterday_count }}": fmt_int(data["parking_yesterday"].get("count")),
        "{{ parking_amount }}": money(data["parking"].get("amount")),
        "{{ parking_active }}": fmt_int(data["parking"].get("active_count")),
        "{{ parking_compare }}": compare_text(data["parking"].get("count"), data["parking_yesterday"].get("count"), " stk"),
        "{{ parking_week_count }}": fmt_int(data["parking_week"].get("count")),
        "{{ parking_week_amount }}": money(data["parking_week"].get("amount")),
        "{{ parking_month_count }}": fmt_int(data["parking_month"].get("count")),
        "{{ parking_month_amount }}": money(data["parking_month"].get("amount")),
        "{{ latest_parking }}": latest_parking,
        "{{ parking_time }}": fmt_time(data["parking_import"].get("updated_at")) if data["parking_import"].get("updated_at") else fmt_time(data["parking"].get("updated_at")),
        "{{ revenue_card }}": revenue_card,
        "{{ energy_icon }}": metric_icon("energy"),
        "{{ energy_watt }}": fmt_watt(data["energy_now"].get("inntak_w")),
        "{{ energy_kwh }}": fmt_kwh(data["energy_today"].get("kwh")),
        "{{ energy_samples }}": fmt_int(data["energy_today"].get("samples")),
        "{{ energy_diff }}": fmt_watt(data["energy_now"].get("differanse_beregnet_w")),
        "{{ energy_time }}": fmt_time(data["energy_now"].get("bucket_start") or data["energy_now"].get("timestamp")),
        "{{ inside_avg }}": fmt_temp(data["inside_avg"]),
        "{{ outside }}": fmt_temp(data["outside"]),
        "{{ outside_sensor }}": fmt_temp(data["outside_sensor"]),
        "{{ yr_temp }}": fmt_temp(data["yr_temp"]),
        "{{ loft }}": fmt_temp(data["vent"].get("temp_loft")),
        "{{ temp_kjeller }}": fmt_temp(data["vent"].get("temp_kjeller")),
        "{{ humidity_kjeller }}": f'{fmt_int(data["vent"].get("humidity_kjeller"))}%' if data["vent"].get("humidity_kjeller") is not None else "-",
        "{{ innluft }}": fmt_temp(data["innluft"]),
        "{{ temp_1etg }}": fmt_temp(data["vent"].get("temp_1etg")),
        "{{ temp_2etg }}": fmt_temp(data["vent"].get("temp_2etg")),
        "{{ temp_vip }}": fmt_temp(data["vent"].get("temp_vip")),
        "{{ humidity_1etg }}": f'{fmt_int(data["vent"].get("humidity_1etg"))}%' if data["vent"].get("humidity_1etg") is not None else "-",
        "{{ humidity_2etg }}": f'{fmt_int(data["vent"].get("humidity_2etg"))}%' if data["vent"].get("humidity_2etg") is not None else "-",
        "{{ humidity_vip }}": f'{fmt_int(data["vent"].get("humidity_vip"))}%' if data["vent"].get("humidity_vip") is not None else "-",
        "{{ humidity_ute }}": f'{fmt_int(data["vent"].get("humidity_ute"))}%' if data["vent"].get("humidity_ute") is not None else "-",
        "{{ humidity_yr }}": f'{fmt_int(data["vent"].get("humidity_yr"))}%' if data["vent"].get("humidity_yr") is not None else "-",
        "{{ temp_time }}": fmt_time(data["vent"].get("bucket_start") or data["vent"].get("timestamp")),
        "{{ lux }}": fmt_int(data["lights"].get("lux")),
        "{{ light_time }}": fmt_time(data["lights"].get("bucket_start") or data["lights"].get("timestamp")),
    }
    for key, value in replacements.items():
        html = html.replace(key, value)
    html = html.replace("{{ light_cards }}", render_state_cards(data["light_items"], "light"))
    html = html.replace("{{ fan_cards }}", render_state_cards(data["fan_items"], "fan"))
    html = html.replace("{{ solroom_door_summary }}", render_solroom_door_summary(data.get("solroom_doors") or []))
    html = html.replace("{{ solroom_door_cards }}", render_door_dashboard_cards(data.get("solroom_doors") or []))
    html = html.replace("{{ door_alarm_summary }}", render_door_alarm_summary(data.get("door_alarm") or {}))
    html = html.replace("{{ door_alarm_cards }}", render_door_alarm_dashboard_cards(data.get("door_alarm") or {}))
    html = html.replace("{{ other_door_summary }}", render_other_door_summary(data.get("other_doors") or []))
    html = html.replace("{{ other_door_cards }}", render_door_dashboard_cards(data.get("other_doors") or []))
    return HTMLResponse(html)


@app.get("/soling", response_class=HTMLResponse)
async def soling_detail(request: Request):
    data = await dashboard_data()
    can_view_money = can_manage(request.state.access_key)
    amount = lambda value: fmt_amount(value) if can_view_money else ""
    session_import_at = data["session_import"].get("updated_at")
    latest_soling_at = data["latest_soling"].get("started_at")
    latest_soling_room = str(data["latest_soling"].get("room") or "").strip()
    latest_soling_detail = f"Rom {latest_soling_room}" if latest_soling_room else fmt_date(latest_soling_at)
    rows = []
    if SOURCE_MODE:
        rows = await many_mappings(
            """
            select started_at, room, duration_minutes, paid_amount_kr
            from sun2_tanning_sessions
            where stat_date = :today
            order by started_at desc
            limit 12
            """,
            {"today": data["now"].date()},
        )
    soling_today_detail = compare_short(
        data["soling"].get("count"),
        data["soling_last_week_same_time"].get("count"),
        "samme tidspunkt forrige uke",
    )
    if can_view_money:
        soling_today_detail = f"{amount(data['soling'].get('amount'))} - {soling_today_detail}"
    body = detail_stats(
        [
            ("Siste soling", fmt_clock(latest_soling_at), latest_soling_detail),
            (
                "I dag",
                fmt_int(data["soling"].get("count")),
                soling_today_detail,
            ),
            (
                "Samme dag forrige uke",
                fmt_int(data["soling_last_week_same_day"].get("count")),
                amount(data["soling_last_week_same_day"].get("amount")),
            ),
            (
                "Samme to uker siden",
                fmt_int(data["soling_two_weeks_same_day"].get("count")),
                amount(data["soling_two_weeks_same_day"].get("amount")),
            ),
            ("Denne uken", fmt_int(data["soling_week"].get("count")), amount(data["soling_week"].get("amount"))),
            ("Forrige uke", fmt_int(data["soling_previous_week"].get("count")), amount(data["soling_previous_week"].get("amount"))),
            ("Denne måneden", fmt_int(data["soling_month"].get("count")), amount(data["soling_month"].get("amount"))),
            ("Forrige måned", fmt_int(data["soling_previous_month"].get("count")), amount(data["soling_previous_month"].get("amount"))),
        ]
    )
    body += f'<p class="detail-updated-line">Sist oppdatert {fmt_clock(session_import_at)} {fmt_date(session_import_at)}</p>'
    if rows:
        body += render_today_soling_list(rows, can_view_money)
    return render_detail_page("Soling", "Dagens solinger og utvikling hittil.", body, icon="sun")


@app.get("/omsetning", response_class=HTMLResponse)
async def revenue_detail(request: Request, week: Optional[str] = None):
    if not can_manage(request.state.access_key):
        return RedirectResponse("/", status_code=303)
    data = await dashboard_data()
    body = detail_stats(
        [
            ("I dag", fmt_amount(data["revenue"].get("today")), f"Sol {fmt_amount(data['soling'].get('amount'))} - park {fmt_amount(data['parking'].get('amount'))}"),
            ("I går", fmt_amount(data["revenue"].get("yesterday")), f"Sol {fmt_amount(data['soling_yesterday'].get('amount'))} - park {fmt_amount(data['parking_yesterday'].get('amount'))}"),
            ("Samme dag forrige uke", fmt_amount(data["revenue"].get("last_week_same_day")), f"Sol {fmt_amount(data['soling_last_week_same_day'].get('amount'))} - park {fmt_amount(data['parking_last_week_same_day'].get('amount'))}"),
            ("Samme to uker siden", fmt_amount(data["revenue"].get("two_weeks_same_day")), f"Sol {fmt_amount(data['soling_two_weeks_same_day'].get('amount'))} - park {fmt_amount(data['parking_two_weeks_same_day'].get('amount'))}"),
            ("Denne uken", fmt_amount(data["revenue"].get("week")), f"Sol {fmt_amount(data['soling_week'].get('amount'))} - park {fmt_amount(data['parking_week'].get('amount'))}"),
            ("Forrige uke", fmt_amount(data["revenue"].get("previous_week")), f"Sol {fmt_amount(data['soling_previous_week'].get('amount'))} - park {fmt_amount(data['parking_previous_week'].get('amount'))}"),
            ("Denne måneden", fmt_amount(data["revenue"].get("month")), f"Sol {fmt_amount(data['soling_month'].get('amount'))} - park {fmt_amount(data['parking_month'].get('amount'))}"),
            ("Forrige måned", fmt_amount(data["revenue"].get("previous_month")), f"Sol {fmt_amount(data['soling_previous_month'].get('amount'))} - park {fmt_amount(data['parking_previous_month'].get('amount'))}"),
        ]
    )
    updated_note = f'<p class="detail-hero-note">Sist oppdatert {fmt_clock(data["revenue_updated_at"])} {fmt_date(data["revenue_updated_at"])}</p>'
    return render_detail_page("Omsetning", "Samlet inntekt fra soling og parkering.", body, icon="revenue", hero_note=updated_note)


@app.get("/omsetning/uke", response_class=HTMLResponse)
async def revenue_week_detail(request: Request, week: Optional[str] = None):
    if not can_manage(request.state.access_key):
        return RedirectResponse("/", status_code=303)
    data = await dashboard_data()
    today = data["now"].date()
    week_start = normalize_week_start(week, today - timedelta(days=today.weekday()))
    snapshot_week = ((data.get("_charts") or {}).get("revenue_week") or {})
    snapshot_week_start = hydrate_value(snapshot_week.get("week_start"))
    if SNAPSHOT_MODE:
        if isinstance(snapshot_week_start, date):
            week_start = snapshot_week_start
        week_rows = snapshot_week.get("rows") or []
    else:
        week_rows = await revenue_week_data(week_start)
    body = render_revenue_week_chart_selectable(week_start, week_rows)
    updated_note = f'<p class="detail-hero-note">Sist oppdatert {fmt_clock(data["revenue_updated_at"])} {fmt_date(data["revenue_updated_at"])}</p>'
    return render_detail_page("Omsetning diagram", "Ukevis omsetning fra soling og parkering.", body, icon="revenue", hero_note=updated_note)


@app.get("/parkering", response_class=HTMLResponse)
async def parking_detail(request: Request, refresh: Optional[str] = None, reason: Optional[str] = None):
    data = await dashboard_data()
    can_view_money = can_manage(request.state.access_key)
    amount = lambda value: fmt_amount(value) if can_view_money else ""
    easypark_status = easypark_downloader_status() if SOURCE_MODE else {}
    parking_import_at = data["parking_import"].get("updated_at")
    parking_failed_at = data["parking_import"].get("last_failed_at")
    parking_next_import_at = easypark_next_run_at(easypark_status)
    next_import_text = (
        f"Neste planlagt: {display_stamp(parking_next_import_at)}"
        if parking_next_import_at
        else "Neste planlagt: -"
    )
    latest_import_failed = isinstance(parking_failed_at, datetime) and (
        not isinstance(parking_import_at, datetime) or parking_failed_at > parking_import_at
    )
    if latest_import_failed:
        import_status_text = f"Siste forsøk feilet. Sist OK: {display_stamp(parking_import_at)}"
    if latest_import_failed:
        import_status_text = f"Siste fors\u00f8k feilet. Sist OK: {display_stamp(parking_import_at)}. {next_import_text}"
    else:
        import_status_text = f"Sist OK: {display_stamp(parking_import_at)}. {next_import_text}"
    rows = []
    if SOURCE_MODE:
        start, end = day_bounds(data["now"].date())
        rows = await many_mappings(
            """
            with dagens as (
                select p.*,
                       upper(replace(coalesce(p.car_license_number, ''), ' ', '')) as plate_key
                from parkering p
                where p.start_time >= :start and p.start_time < :end
            )
            select d.start_time,
                   d.end_time,
                   d.car_license_number,
                   d.fee_inc_vat,
                   d.parking_time_min,
                   d.status,
                   v.car_info_data,
                   k.merke,
                   k.modell,
                   k.typebetegnelse,
                   k.farge,
                   k.forstegangsregistrert_norge,
                   k.svv_teknisk_gyldig_fra,
                   case
                       when d.plate_key = '' then 0
                       else (
                           select count(*)
                           from parkering previous
                           where upper(replace(coalesce(previous.car_license_number, ''), ' ', '')) = d.plate_key
                             and (
                                 previous.start_time < d.start_time
                                 or (previous.start_time = d.start_time and previous.id < d.id)
                             )
                       )
                   end as previous_parking_count
            from dagens d
            left join kjoretoy v on v.plate = d.plate_key
            left join kjoretoy_nokkeldata k on k.plate = d.plate_key
            order by
                case
                    when lower(coalesce(d.status, '')) in ('ongoing', 'active', 'started') then 0
                    else 1
                end,
                d.start_time desc,
                d.id desc
            limit 30
            """,
            {"start": start, "end": end},
        )
    can_refresh = SOURCE_MODE and can_manage(request.state.access_key)
    cooldown_remaining = parking_refresh_cooldown_remaining_seconds()
    refresh_state = "ready"
    refresh_button_text = "Oppdater tall"
    refresh_status_text = f"Klar for oppdatering. {import_status_text}"
    refresh_disabled = ""
    if parking_refresh_lock.locked() or easypark_status.get("running") is True:
        refresh_state = "busy"
        refresh_button_text = "Oppdaterer..."
        refresh_status_text = f"Oppdatering kjører nå. {import_status_text}"
        refresh_disabled = " disabled"
    elif cooldown_remaining > 0:
        refresh_state = "cooldown"
        refresh_button_text = "Vent litt"
        refresh_status_text = f"Klar igjen om {format_duration_short(cooldown_remaining)}. {import_status_text}"
        refresh_disabled = " disabled"
    refresh_label = {
        "ok": "Oppdatering startet/ferdig.",
        "busy": "EasyPark jobber allerede.",
        "cooldown": "Oppdatering nylig sendt. Vent litt før neste forsøk.",
        "denied": "",
        "error": f"Oppdatering feilet: {friendly_easypark_error(reason or '', easypark_status)}",
    }.get(refresh or "", "")
    button = (
        f"""
        <form method="post" action="/parkering/oppdater" class="detail-action is-{refresh_state}">
          <button type="submit"{refresh_disabled}>{escape(refresh_button_text)}</button>
          <small>{escape(refresh_status_text)}</small>
        </form>
        """
        if can_refresh
        else ""
    )
    if refresh_label:
        button += f'<p class="notice">{escape(refresh_label)}</p>'
    parking_today_detail = compare_short(
        data["parking"].get("count"),
        data["parking_last_week_same_time"].get("count"),
        "samme tidspunkt forrige uke",
    )
    if can_view_money:
        parking_today_detail = f"{amount(data['parking'].get('amount'))} - {parking_today_detail}"
    body = detail_stats(
        [
            (
                "I dag",
                fmt_int(data["parking"].get("count")),
                parking_today_detail,
            ),
            ("I går", fmt_int(data["parking_yesterday"].get("count")), amount(data["parking_yesterday"].get("amount"))),
            (
                "Samme dag forrige uke",
                fmt_int(data["parking_last_week_same_day"].get("count")),
                amount(data["parking_last_week_same_day"].get("amount")),
            ),
            (
                "Samme to uker siden",
                fmt_int(data["parking_two_weeks_same_day"].get("count")),
                amount(data["parking_two_weeks_same_day"].get("amount")),
            ),
            ("Denne uken", fmt_int(data["parking_week"].get("count")), amount(data["parking_week"].get("amount"))),
            ("Forrige uke", fmt_int(data["parking_previous_week"].get("count")), amount(data["parking_previous_week"].get("amount"))),
            ("Denne måneden", fmt_int(data["parking_month"].get("count")), amount(data["parking_month"].get("amount"))),
            ("Forrige måned", fmt_int(data["parking_previous_month"].get("count")), amount(data["parking_previous_month"].get("amount"))),
        ]
    )
    body += (
        f'<p class="detail-updated-line">Sist oppdatert {fmt_clock(parking_import_at)} '
        f'{fmt_date(parking_import_at)} - {escape(next_import_text)}</p>'
    )
    body += button
    if latest_import_failed:
        body += f'<p class="notice">{escape(import_status_text)}</p>'
    if SNAPSHOT_MODE:
        return render_detail_page("Parkering", "Dagens parkeringer med trygg manuell oppdatering.", body, icon="parking")
    body += render_parking_vehicle_list(rows, can_view_money)
    return render_detail_page("Parkering", "Dagens parkeringer med trygg manuell oppdatering.", body, icon="parking")


@app.post("/parkering/oppdater")
async def parking_refresh(request: Request):
    global parking_refresh_last_started_monotonic
    if SNAPSHOT_MODE:
        return RedirectResponse("/parkering?refresh=denied", status_code=303)
    if not can_manage(request.state.access_key):
        return RedirectResponse("/parkering?refresh=denied", status_code=303)
    if parking_refresh_lock.locked():
        return RedirectResponse("/parkering?refresh=busy", status_code=303)
    async with parking_refresh_lock:
        now = time.monotonic()
        if (
            parking_refresh_last_started_monotonic is not None
            and now - parking_refresh_last_started_monotonic < PARKING_REFRESH_COOLDOWN_SECONDS
        ):
            return RedirectResponse("/parkering?refresh=cooldown", status_code=303)
        parking_refresh_last_started_monotonic = now

        from_day, to_day = easypark_period()
        outcome = "error"
        reason = "unknown"
        for attempt in range(2):
            try:
                result = await asyncio.to_thread(
                    easypark_downloader_request,
                    "/queue-sync-period",
                    {"from_date": from_day.isoformat(), "to_date": to_day.isoformat()},
                    10,
                )
                status = result.get("status")
                reason = ""
                if status == "busy":
                    easypark_status = await asyncio.to_thread(easypark_downloader_status)
                    if attempt == 0 and easypark_status.get("running") is not True:
                        await asyncio.sleep(2)
                        continue
                    outcome = "busy"
                    break
                if status == "error":
                    reason = classify_easypark_error(result.get("detail") or result.get("last_error")) or "unknown"
                    if attempt == 0 and should_retry_easypark_refresh(reason):
                        await wait_for_easypark_ready()
                        continue
                    outcome = "error"
                    break
                outcome = "ok"
                break
            except Exception as exc:
                reason = classify_easypark_error(str(exc)) or "unavailable"
                if attempt == 0 and should_retry_easypark_refresh(reason):
                    await wait_for_easypark_ready()
                    continue
                outcome = "error"
                break
    query = {"refresh": outcome}
    if outcome == "error" and reason:
        query["reason"] = reason
    return RedirectResponse(f"/parkering?{urlencode(query)}", status_code=303)


@app.get("/energi", response_class=HTMLResponse)
async def energy_detail(request: Request):
    data = await dashboard_data()
    now = data["energy_now"]
    body = detail_stats(
        [
            ("Inntak nå", fmt_watt(now.get("inntak_w")), fmt_time(now.get("bucket_start") or now.get("timestamp"))),
            ("I dag", fmt_kwh(data["energy_today"].get("kwh")), f"{fmt_int(data['energy_today'].get('samples'))} målinger"),
            ("Belysning", fmt_watt(now.get("belysning_w")), "nå"),
            ("Varmepumper", fmt_watt(now.get("varmepumper_w")), "nå"),
            ("Avfukter", fmt_watt(now.get("avfukter_w")), "nå"),
        ]
    )
    body += f'<p class="notice">Beregnet differanse akkurat nå: <strong>{fmt_watt(now.get("differanse_beregnet_w"))}</strong>.</p>'
    return render_detail_page("Energi", "Strømstatus fra siste HC3-avlesning.", body, icon="energy")


@app.get("/temperatur", response_class=HTMLResponse)
async def temperature_detail(request: Request):
    data = await dashboard_data()
    if SNAPSHOT_MODE:
        ranges = ((data.get("_ranges") or {}).get("temperature_today") or {})
    else:
        ranges = await temperature_ranges(data["now"].date())
    body = detail_stats(
        [
            ("Inne nå", fmt_temp(data["inside_avg"]), f"{fmt_temp(ranges.get('min_inne'))} - {fmt_temp(ranges.get('max_inne'))}"),
            ("Ute nå", fmt_temp(data["outside"]), f"{fmt_temp(ranges.get('min_ute'))} - {fmt_temp(ranges.get('max_ute'))}"),
            ("Loft nå", fmt_temp(data["vent"].get("temp_loft")), f"{fmt_temp(ranges.get('min_loft'))} - {fmt_temp(ranges.get('max_loft'))}"),
            ("Fukt inne", f"{fmt_int(data['vent'].get('humidity_1etg'))}%" if data["vent"].get("humidity_1etg") is not None else "-", f"2.etg {fmt_int(data['vent'].get('humidity_2etg'))}% / VIP {fmt_int(data['vent'].get('humidity_vip'))}%"),
            ("Fukt ute/Yr", f"{fmt_int(data['vent'].get('humidity_ute'))}%" if data["vent"].get("humidity_ute") is not None else "-", f"Yr {fmt_int(data['vent'].get('humidity_yr'))}%"),
            ("Kjeller nå", fmt_temp(data["vent"].get("temp_kjeller")), f"Fukt {fmt_int(data['vent'].get('humidity_kjeller'))}%" if data["vent"].get("humidity_kjeller") is not None else "Fukt -"),
            ("Innluft", fmt_temp(data["innluft"]), f"Oppdatert {fmt_time(data['vent'].get('bucket_start') or data['vent'].get('timestamp'))}"),
        ]
    )
    return render_detail_page("Temperatur", "Nåverdier og spenn hittil i dag.", body, icon="temperature")


@app.get("/lys", response_class=HTMLResponse)
async def light_detail(request: Request):
    data = await dashboard_data()
    events = []
    if SOURCE_MODE:
        events = await many_mappings(
            """
            select timestamp, device_name, action, lux, reason
            from utelys_events
            order by timestamp desc
            limit 10
            """
        )
    body = f'<section class="section-block"><div class="section-title-row"><h2>LYS</h2><div class="lux-pill"><span>Lux</span><strong>{fmt_int(data["lights"].get("lux"))}</strong></div></div><div class="state-grid">{render_state_cards(data["light_items"], "light")}</div><small class="card-time">Oppdatert {fmt_time(data["lights"].get("bucket_start") or data["lights"].get("timestamp"))}</small></section>'
    if SNAPSHOT_MODE:
        return render_detail_page("Lys", "Status og siste hendelser.", body)
    body += render_list(
        "Siste lysendringer",
        [
            (
                fmt_time(row.get("timestamp")),
                escape(str(row.get("device_name") or "Lys")),
                escape(f"{row.get('action') or ''} · lux {fmt_int(row.get('lux'))} · {row.get('reason') or ''}"),
            )
            for row in events
        ],
    )
    return render_detail_page("Lys", "Status og siste hendelser.", body)


@app.get("/ventilasjon", response_class=HTMLResponse)
async def ventilation_detail(request: Request):
    data = await dashboard_data()
    events = []
    if SOURCE_MODE:
        events = await many_mappings(
            """
            select timestamp, device_name, action, mode, reason
            from ventilasjon_events
            order by timestamp desc
            limit 10
            """
        )
    body = f'<section class="section-block"><div class="section-title-row"><h2>VENTILASJON</h2></div><div class="state-grid">{render_state_cards(data["fan_items"], "fan")}</div><small class="card-time">Oppdatert {fmt_time(data["vent"].get("bucket_start") or data["vent"].get("timestamp"))}</small></section>'
    if SNAPSHOT_MODE:
        return render_detail_page("Ventilasjon", "Status og siste hendelser.", body)
    body += render_list(
        "Siste viftehendelser",
        [
            (
                fmt_time(row.get("timestamp")),
                escape(str(row.get("device_name") or "Vifte")),
                escape(f"{row.get('action') or ''} · {row.get('mode') or ''} · {row.get('reason') or ''}"),
            )
            for row in events
        ],
    )
    return render_detail_page("Ventilasjon", "Status og siste hendelser.", body)


@app.get("/solrom", response_class=HTMLResponse)
async def solroom_doors_detail(request: Request):
    data = await dashboard_data()
    statuses = list(data.get("solroom_doors") or [])
    latest = max(
        (
            item.get("timestamp")
            for item in statuses
            if isinstance(item.get("timestamp"), datetime)
        ),
        default=None,
    )
    body = detail_stats(
        [
            ("Ledige", fmt_int(sum(1 for item in statuses if item.get("state") == "open")), "dør åpen"),
            ("I bruk", fmt_int(sum(1 for item in statuses if item.get("state") == "closed")), "dør lukket"),
            ("Ukjent", fmt_int(sum(1 for item in statuses if item.get("state") == "unknown")), "mangler siste status"),
            ("Sist endret", fmt_clock(latest), fmt_date(latest)),
        ]
    )
    body += render_door_overview(statuses, "/solrom")
    return render_detail_page("Solrom", "Status og siste endring per solrom.", body, icon="door")


@app.get("/solrom/{device_key}", response_class=HTMLResponse)
async def solroom_door_detail(device_key: str, request: Request):
    config = SOLROOM_DOOR_BY_KEY.get(device_key)
    if not config:
        raise HTTPException(status_code=404, detail="Ukjent solrom")
    data = await dashboard_data()
    statuses = list(data.get("solroom_doors") or [])
    status = next((item for item in statuses if item.get("device_key") == device_key), None)
    if not status:
        status = door_status_payload(config, None, local_now())
    events = await solroom_door_events(device_key, 80) if SOURCE_MODE else []
    body = detail_stats(
        [
            ("Status", str(status.get("state_label") or "Ukjent"), str(status.get("age_label") or "-")),
            ("Sist endret", str(status.get("last_changed") or "-"), str(status.get("section_title") or "")),
            (
                "Batteri",
                f"{float(status['battery_level']):.0f}%" if status.get("battery_level") is not None else "-",
                "sensor",
            ),
            ("Hendelser", fmt_int(len(events)), "nyeste øverst"),
        ]
    )
    if SNAPSHOT_MODE:
        body += '<p class="notice">Detaljert hendelseshistorikk er bare tilgjengelig når mobilappen leser direkte fra Fibaro10-databasen.</p>'
    body += render_door_event_list(events, "Siste dørhendelser")
    return render_detail_page(str(config.get("title") or "Solrom"), "Siste statusendringer for valgt solrom.", body, icon="door")


@app.get("/dorer", response_class=HTMLResponse)
async def other_doors_detail(request: Request):
    data = await dashboard_data()
    statuses = list(data.get("other_doors") or [])
    latest = max(
        (
            item.get("timestamp")
            for item in statuses
            if isinstance(item.get("timestamp"), datetime)
        ),
        default=None,
    )
    body = detail_stats(
        [
            ("Åpne", fmt_int(sum(1 for item in statuses if item.get("state") == "open")), "andre dører"),
            ("Lukket", fmt_int(sum(1 for item in statuses if item.get("state") == "closed")), "andre dører"),
            ("Ukjent", fmt_int(sum(1 for item in statuses if item.get("state") == "unknown")), "mangler siste status"),
            ("Sist endret", fmt_clock(latest), fmt_date(latest)),
        ]
    )
    body += render_door_overview(statuses, "/dorer")
    return render_detail_page("Andre dører", "Status og siste endring per dør.", body, icon="door")


@app.get("/dorer/alarm", response_class=HTMLResponse)
async def door_alarm_detail(request: Request):
    data = await dashboard_data()
    alarm_data = dict(data.get("door_alarm") or {})
    day_control = dict(data.get("door_day_control") or {})
    summary = dict(day_control.get("summary") or {})
    threshold = alarm_data.get("threshold_minutes") or SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES
    threshold_text = f"{float(threshold):g}"
    body = detail_stats(
        [
            ("Perioder", fmt_int(summary.get("rows")), "dør og soltime"),
            ("Avvik", fmt_int(summary.get("deviations")), "bør kontrolleres"),
            ("Alarm", fmt_int(summary.get("alarms")), "registrert i dag"),
            ("Mangler", fmt_int(summary.get("missing")), "dør eller soltime"),
        ]
    )
    subscribe_url = str(alarm_data.get("subscribe_url") or ntfy_subscribe_url(NTFY_DOORS_TOPIC, "SUN2 dørvarsler"))
    body += f"""
    <section class="section-block door-alarm-subscribe">
      <a class="primary-action" href="{escape(subscribe_url)}">Abonner på dørvarsler</a>
      <small>Varsel sendes når et solrom har vært lukket mer enn {escape(threshold_text)} min uten koblet Sun2-time.</small>
    </section>
    """
    body += render_door_day_control(day_control)
    return render_detail_page("Døralarm", "Dagens dørperioder, soltimer, avvik og alarmer.", body, icon="door")


@app.get("/dorer/{device_key}", response_class=HTMLResponse)
async def other_door_detail(device_key: str, request: Request):
    config = OTHER_DOOR_BY_KEY.get(device_key)
    if not config:
        raise HTTPException(status_code=404, detail="Ukjent dør")
    data = await dashboard_data()
    statuses = list(data.get("other_doors") or [])
    status = next((item for item in statuses if item.get("device_key") == device_key), None)
    if not status:
        status = door_status_payload(config, None, local_now())
    events = await other_door_events(device_key, 80) if SOURCE_MODE else []
    body = detail_stats(
        [
            ("Status", str(status.get("state_label") or "Ukjent"), str(status.get("age_label") or "-")),
            ("Sist endret", str(status.get("last_changed") or "-"), str(status.get("device_name") or "")),
            (
                "Batteri",
                f"{float(status['battery_level']):.0f}%" if status.get("battery_level") is not None else "-",
                "sensor",
            ),
            ("Hendelser", fmt_int(len(events)), "nyeste øverst"),
        ]
    )
    if SNAPSHOT_MODE:
        body += '<p class="notice">Detaljert hendelseshistorikk er bare tilgjengelig når mobilappen leser direkte fra Fibaro10-databasen.</p>'
    body += render_door_event_list(events)
    return render_detail_page(str(config.get("title") or "Dør"), "Siste statusendringer for valgt dør.", body, icon="door")


def render_state_cards(items: list[tuple[str, Any]], icon_class: str) -> str:
    cards = []
    for label, value in items:
        cards.append(
            f"""
            <article class="state-card {state_class(value)}">
                <span class="state-dot"></span>
                <div>
                    <strong>{label}</strong>
                </div>
                <small class="state-pill">{state_label(value)}</small>
            </article>
            """
        )
    return "\n".join(cards)


def detail_stats(items: list[tuple[str, str, str]]) -> str:
    cards = []
    for label, value, subtext in items:
        subtext_html = f"<small>{escape(subtext)}</small>" if subtext else ""
        cards.append(
            f"""
            <article>
                <span>{escape(label)}</span>
                <strong>{escape(value)}</strong>
                {subtext_html}
            </article>
            """
        )
    return f'<section class="insight-grid detail-stats">{"".join(cards)}</section>'


def render_list(title: str, rows: list[tuple[str, str, str]]) -> str:
    if not rows:
        content = '<p class="empty-list">Ingen registreringer akkurat nå.</p>'
    else:
        content = "".join(
            f"""
            <li>
                <time>{escape(time_text)}</time>
                <strong>{main}</strong>
                {f"<small>{detail}</small>" if detail else ""}
            </li>
            """
            for time_text, main, detail in rows
        )
    return f'<section class="section-block detail-list"><h2>{escape(title)}</h2><ul>{content}</ul></section>'


def render_today_soling_list(rows: list[dict[str, Any]], can_view_money: bool) -> str:
    return render_list(
        "Siste solinger",
        [
            (
                fmt_clock(row.get("started_at")),
                escape(str(row.get("room") or "Ukjent rom")),
                f"{float(row.get('duration_minutes') or 0):.0f} min"
                + (f" - {fmt_amount(row.get('paid_amount_kr'))}" if can_view_money else ""),
            )
            for row in rows
        ],
    )


def render_parking_vehicle_list(rows: list[dict[str, Any]], can_view_money: bool) -> str:
    if not rows:
        content = '<p class="empty-list">Ingen parkeringer registrert i dag.</p>'
    else:
        items = []
        ordered_rows = sorted(
            rows,
            key=lambda item: item.get("start_time").isoformat()
            if isinstance(item.get("start_time"), datetime)
            else str(item.get("start_time") or ""),
            reverse=True,
        )
        ordered_rows.sort(key=lambda item: 0 if parking_status_is_active(item.get("status")) else 1)
        for row in ordered_rows:
            plate = str(row.get("car_license_number") or "Uten regnr").strip()
            status = parking_status_label(row.get("status"))
            vehicle = parking_vehicle_summary(row)
            previous_count = parking_previous_count_label(row.get("previous_parking_count"))
            duration = f"{float(row.get('parking_time_min') or 0):.0f} min"
            status_class = " is-active" if parking_status_is_active(row.get("status")) else ""
            status_html = f'<span class="parking-status{status_class}">{escape(status)}</span>' if status else ""
            amount_html = (
                f'<strong class="parking-row-amount">{escape(fmt_amount(row.get("fee_inc_vat")))} kr</strong>'
                if can_view_money
                else ""
            )
            items.append(
                f"""
                <li class="parking-vehicle-row">
                    <time>{escape(mobile_clock(row.get("start_time")))}</time>
                    <div class="parking-row-main">
                        <div class="parking-row-heading"><strong>{escape(plate)}</strong>{status_html}</div>
                        <small>{escape(vehicle)}</small>
                        <small class="parking-row-history">{escape(previous_count)}</small>
                    </div>
                    <div class="parking-row-facts">
                        {amount_html}
                        <span>{escape(duration)}</span>
                    </div>
                </li>
                """
            )
        content = "".join(items)
    return f'<section class="section-block detail-list parking-vehicle-list"><h2>Dagens parkeringer</h2><ul>{content}</ul></section>'


def render_other_door_summary(statuses: list[dict[str, Any]]) -> str:
    if not statuses:
        return "Ingen dørdata"
    open_count = sum(1 for item in statuses if item.get("state") == "open")
    closed_count = sum(1 for item in statuses if item.get("state") == "closed")
    unknown_count = sum(1 for item in statuses if item.get("state") == "unknown")
    parts = [f"{open_count} åpne", f"{closed_count} lukket"]
    if unknown_count:
        parts.append(f"{unknown_count} ukjent")
    return " · ".join(parts)


def render_solroom_door_summary(statuses: list[dict[str, Any]]) -> str:
    if not statuses:
        return "Ingen romdata"
    available_count = sum(1 for item in statuses if item.get("state") == "open")
    busy_count = sum(1 for item in statuses if item.get("state") == "closed")
    unknown_count = sum(1 for item in statuses if item.get("state") == "unknown")
    parts = [f"{available_count} ledige", f"{busy_count} i bruk"]
    if unknown_count:
        parts.append(f"{unknown_count} ukjent")
    return " · ".join(parts)


def render_door_dashboard_cards(statuses: list[dict[str, Any]]) -> str:
    if not statuses:
        return '<p class="empty-list">Ingen dørdata akkurat nå.</p>'
    newest = sorted(
        statuses,
        key=lambda item: datetime_sort_value(item.get("timestamp")),
        reverse=True,
    )[:4]
    cards = []
    for item in newest:
        group_class = f" is-{escape(str(item.get('group_key') or 'door'))}"
        cards.append(
            f"""
            <article class="door-mini-card is-{escape(str(item.get("state") or "unknown"))}{group_class}">
                <strong>{escape(str(item.get("title") or ""))}</strong>
                <span>{escape(str(item.get("state_label") or "Ukjent"))}</span>
                <small>{escape(str(item.get("age_label") or "-"))}</small>
            </article>
            """
        )
    return f'<div class="door-mini-grid">{"".join(cards)}</div>'


def render_door_alarm_summary(alarm_data: dict[str, Any]) -> str:
    summary = dict(alarm_data.get("summary") or {})
    alarms = int(summary.get("alarms") or 0)
    watch = int(summary.get("watch") or 0)
    if alarms:
        return f"{alarms} alarm"
    if watch:
        return f"{watch} følger"
    return "Ingen alarm"


def render_door_alarm_dashboard_cards(alarm_data: dict[str, Any]) -> str:
    items = list(alarm_data.get("alarms") or alarm_data.get("watch") or [])[:4]
    if not items:
        return '<p class="empty-list">Ingen solrom er lukket over alarmgrensen uten soltime.</p>'
    cards = []
    for item in items:
        state_class = "alarm" if item.get("alarm_active") else "watch"
        state_text = "Alarm" if item.get("alarm_active") else "Følger opp"
        cards.append(
            f"""
            <article class="door-mini-card is-closed is-solrom is-{state_class}">
                <strong>{escape(str(item.get("title") or ""))}</strong>
                <span>{state_text}</span>
                <small>Lukket {escape(str(item.get("duration_label") or "-"))}</small>
            </article>
            """
        )
    return f'<div class="door-mini-grid">{"".join(cards)}</div>'


def mobile_clock(value: Any) -> str:
    return value.strftime("%H:%M") if isinstance(value, datetime) else "-"


def mobile_session_range(session: dict[str, Any]) -> str:
    started_at = mobile_clock(session.get("started_at"))
    ended_at = mobile_clock(session.get("ended_at"))
    return f"{started_at}–{ended_at}" if started_at != "-" and ended_at != "-" else started_at


def mobile_exit_delta(value: Any) -> str:
    try:
        rounded = round(float(value))
    except (TypeError, ValueError):
        return ""
    if rounded == 0:
        return "0 min mot forventet"
    return f"{rounded:+d} min mot forventet"


def render_door_day_control(day_control: dict[str, Any]) -> str:
    items = list(day_control.get("rows") or [])
    if not items:
        return '<section class="section-block door-control-list"><h2>Dagens dørperioder</h2><p class="empty-list">Ingen dørperioder eller soltimer i dag.</p></section>'

    cards = []
    for item in items:
        session = dict(item.get("session") or {})
        alarm = dict(item.get("alarm") or {})
        severity = str(item.get("severity") or "ok")
        status = str(item.get("status") or "OK")
        opened_text = mobile_clock(item.get("opened_at")) if item.get("opened_at") else "Pågår"
        session_text = mobile_session_range(session) if session else "Ikke funnet"
        duration_minutes = session.get("duration_minutes")
        session_detail = ""
        if session:
            duration_text = f"{float(duration_minutes):g} min" if duration_minutes is not None else "varighet ukjent"
            bed_text = f"seng {session.get('sun2_bed_id')}" if session.get("sun2_bed_id") else "seng ukjent"
            session_detail = f"{duration_text} · {bed_text}"
        alarm_html = ""
        if alarm:
            alarm_label = "Feilalarm" if alarm.get("outcome") == "false_positive" else "Alarm"
            alarm_type = "Overtid" if alarm.get("alarm_type") == "overstay" else "Uten soltime"
            notification_text = {
                "sent": "varsel sendt",
                "failed": "varsling feilet",
                "not_sent": "varsel ikke sendt",
                "unknown": "eldre varselstatus ukjent",
            }.get(str(alarm.get("notification_status") or ""), "")
            alarm_html = f"""
                <div class="door-control-alarm">
                    <strong>{escape(alarm_label)} {escape(mobile_clock(alarm.get('detected_at')))} · {escape(alarm_type)}</strong>
                    {f'<small>{escape(notification_text)}</small>' if notification_text else ''}
                </div>
            """
        delta_text = mobile_exit_delta(item.get("exit_delta_minutes"))
        cards.append(
            f"""
            <article class="door-control-row is-{escape(severity)}">
                <header>
                    <strong>{escape(str(item.get("title") or "Solrom"))}</strong>
                    <em>{escape(status)}</em>
                </header>
                <dl>
                    <div><dt>Lukket</dt><dd>{escape(mobile_clock(item.get("closed_at")))}</dd></div>
                    <div><dt>Soltime</dt><dd>{escape(session_text)}{f'<small>{escape(session_detail)}</small>' if session_detail else ''}</dd></div>
                    <div><dt>Forventet ut</dt><dd>{escape(mobile_clock(item.get("expected_exit_at")))}</dd></div>
                    <div><dt>Åpnet</dt><dd>{escape(opened_text)}<small>{escape(str(item.get("duration_label") or "-"))}</small></dd></div>
                </dl>
                <footer>
                    <strong>{escape(str(item.get("deviation") or "Ingen avvik"))}</strong>
                    {f'<small>{escape(delta_text)}</small>' if delta_text else ''}
                </footer>
                {alarm_html}
            </article>
            """
        )
    return f'<section class="section-block door-control-list"><h2>Dagens dørperioder</h2><div>{"".join(cards)}</div></section>'


def render_door_overview(statuses: list[dict[str, Any]], base_path: str) -> str:
    if not statuses:
        return '<section class="section-block"><p class="empty-list">Ingen dørdata akkurat nå.</p></section>'
    cards = []
    for item in statuses:
        state = str(item.get("state") or "unknown")
        title = str(item.get("title") or item.get("device_key") or "Dør")
        state_label = str(item.get("state_label") or "Ukjent")
        last_changed = str(item.get("last_changed") or "-")
        age_label = str(item.get("age_label") or "-")
        section = str(item.get("section_title") or "").strip()
        section_html = f" · {escape(section)}" if section else ""
        group_class = f" is-{escape(str(item.get('group_key') or 'door'))}"
        href = f"{base_path.rstrip('/')}/{escape(str(item.get('device_key') or ''))}"
        cards.append(
            f"""
            <a class="other-door-card is-{escape(state)}{group_class}" href="{href}">
                <div>
                    <span>Status{section_html}</span>
                    <strong>{escape(title)}</strong>
                </div>
                <em>{escape(state_label)}</em>
                <small>Sist endret {escape(last_changed)} · {escape(age_label)}</small>
            </a>
            """
        )
    return f'<section class="other-door-grid">{"".join(cards)}</section>'


def render_door_event_list(rows: list[dict[str, Any]], title: str = "Siste hendelser") -> str:
    if not rows:
        content = '<p class="empty-list">Ingen statusendringer registrert.</p>'
    else:
        items = []
        now = local_now()
        for row in rows:
            state = door_state_info(row)
            timestamp = row.get("timestamp")
            battery = row.get("battery_level")
            detail_parts = [relative_time_label(timestamp, now)]
            if battery is not None:
                detail_parts.append(f"batteri {float(battery):.0f}%")
            source = str(row.get("source") or "").strip()
            if source:
                detail_parts.append(source)
            items.append(
                f"""
                <li class="door-event-row is-{escape(state['state'])}">
                    <time>{escape(display_stamp(timestamp))}</time>
                    <strong>{escape(state["label"])}</strong>
                    <small>{escape(" · ".join(detail_parts))}</small>
                </li>
                """
            )
        content = "".join(items)
    return f'<section class="section-block detail-list door-event-list"><h2>{escape(title)}</h2><ul>{content}</ul></section>'


def render_revenue_week_chart(week_start: date, rows: list[dict[str, Any]]) -> str:
    weekday_labels = ["Man", "Tir", "Ons", "Tor", "Fre", "Lør", "Søn"]
    scale_max = 25000.0
    week_end = week_start + timedelta(days=6)
    previous_url = f"/omsetning?{urlencode({'week': (week_start - timedelta(days=7)).isoformat()})}"
    next_url = f"/omsetning?{urlencode({'week': (week_start + timedelta(days=7)).isoformat()})}"
    today = local_now().date()
    today_week = today - timedelta(days=today.weekday())
    today_url = f"/omsetning?{urlencode({'week': today_week.isoformat()})}"
    bars = []
    for row in rows:
        day = row["day"]
        sol = float(row.get("sol") or 0)
        parking = float(row.get("parking") or 0)
        total = sol + parking
        sol_height = 0 if sol <= 0 else max(3.0, sol / scale_max * 100)
        parking_height = 0 if parking <= 0 else max(3.0, parking / scale_max * 100)
        if sol_height + parking_height > 100:
            scale = 100 / (sol_height + parking_height)
            sol_height *= scale
            parking_height *= scale
        bars.append(
            f"""
            <article class="revenue-day">
                <div class="revenue-bar" aria-label="{weekday_labels[day.weekday()]} {day.strftime('%d.%m')} omsetning {fmt_amount(total)}">
                    <span class="revenue-segment parking" style="height:{parking_height:.2f}%"></span>
                    <span class="revenue-segment sun" style="height:{sol_height:.2f}%"></span>
                </div>
                <strong>{fmt_amount(total)}</strong>
                <span>{weekday_labels[day.weekday()]} {day.strftime('%d.%m')}</span>
                <small>Sol {fmt_amount(sol)} · park {fmt_amount(parking)}</small>
            </article>
            """
        )
    return f"""
    <section class="section-block revenue-week-chart">
        <header>
            <div>
                <h2>Uke {week_start.strftime('%d.%m')} - {week_end.strftime('%d.%m')}</h2>
                <p>Omsetning per dag fordelt på soling og parkering. Fast skala til 25 000.</p>
            </div>
            <nav class="revenue-week-nav" aria-label="Velg uke">
                <a href="{previous_url}">Forrige</a>
                <a href="{today_url}">Denne uken</a>
                <a href="{next_url}">Neste</a>
            </nav>
        </header>
        <div class="revenue-legend">
            <span><i class="sun"></i>Soling</span>
            <span><i class="parking"></i>Parkering</span>
        </div>
        <div class="revenue-bars">{"".join(bars)}</div>
    </section>
    """


def render_revenue_week_chart_selectable(week_start: date, rows: list[dict[str, Any]]) -> str:
    weekday_labels = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "L\u00f8rdag", "S\u00f8ndag"]
    scale_max = 25000.0
    week_end = week_start + timedelta(days=6)
    iso_year, iso_week, _ = week_start.isocalendar()
    previous_url = f"/omsetning/uke?{urlencode({'week': (week_start - timedelta(days=7)).isoformat()})}"
    next_url = f"/omsetning/uke?{urlencode({'week': (week_start + timedelta(days=7)).isoformat()})}"
    today = local_now().date()
    today_week = today - timedelta(days=today.weekday())
    today_url = f"/omsetning/uke?{urlencode({'week': today_week.isoformat()})}"
    selected_day = today if week_start <= today <= week_end else week_start
    selected_row = next((row for row in rows if row["day"] == selected_day), rows[0])

    def day_label(day: date) -> str:
        return f"{weekday_labels[day.weekday()]} {day.strftime('%d.%m.%Y')}"

    def distribution_values(row: dict[str, Any]) -> dict[str, str]:
        sol = float(row.get("sol") or 0)
        parking = float(row.get("parking") or 0)
        sol_count = int(row.get("sol_count") or 0)
        parking_count = int(row.get("parking_count") or 0)
        return {
            "label": day_label(row["day"]),
            "total": fmt_amount(sol + parking),
            "sol": fmt_amount(sol),
            "sol_count": f"{fmt_int(sol_count)} solinger",
            "parking": fmt_amount(parking),
            "parking_count": f"{fmt_int(parking_count)} parkeringer",
        }

    week_sol = sum(float(row.get("sol") or 0) for row in rows)
    week_parking = sum(float(row.get("parking") or 0) for row in rows)
    week_total = week_sol + week_parking

    def share_text(value: float) -> str:
        if week_total <= 0:
            return "0% av total"
        return f"{value / week_total * 100:.0f}% av total"

    selected = distribution_values(selected_row)
    bars = []
    for row in rows:
        day = row["day"]
        sol = float(row.get("sol") or 0)
        parking = float(row.get("parking") or 0)
        total = sol + parking
        sol_height = 0 if sol <= 0 else max(3.0, sol / scale_max * 100)
        parking_height = 0 if parking <= 0 else max(3.0, parking / scale_max * 100)
        if sol_height + parking_height > 100:
            scale = 100 / (sol_height + parking_height)
            sol_height *= scale
            parking_height *= scale
        values = distribution_values(row)
        selected_class = " is-selected" if day == selected_day else ""
        aria_pressed = "true" if day == selected_day else "false"
        bars.append(
            f"""
            <button class="revenue-day{selected_class}" type="button" data-revenue-day
                data-label="{escape(values['label'])}"
                data-total="{escape(values['total'])}"
                data-sol="{escape(values['sol'])}"
                data-sol-count="{escape(values['sol_count'])}"
                data-parking="{escape(values['parking'])}"
                data-parking-count="{escape(values['parking_count'])}"
                aria-pressed="{aria_pressed}"
                aria-label="Velg {escape(values['label'])}, omsetning {escape(fmt_amount(total))}">
                <span class="revenue-bar">
                    <span class="revenue-segment parking" style="height:{parking_height:.2f}%"></span>
                    <span class="revenue-segment sun" style="height:{sol_height:.2f}%"></span>
                </span>
            </button>
            """
        )
    return f"""
    <section class="section-block revenue-week-chart">
        <header>
            <div>
                <h2>{iso_year} · Uke {iso_week} · {week_start.strftime('%d.%m')} - {week_end.strftime('%d.%m')}</h2>
                <p>Omsetning per dag fordelt p\u00e5 soling og parkering.</p>
            </div>
            <nav class="revenue-week-nav" aria-label="Velg uke">
                <a href="{previous_url}">Forrige</a>
                <a href="{today_url}">Denne uken</a>
                <a href="{next_url}">Neste</a>
            </nav>
        </header>
        <div class="revenue-legend">
            <span><i class="sun"></i>Soling</span>
            <span><i class="parking"></i>Parkering</span>
        </div>
        <div class="revenue-week-summary">
            <article>
                <span>Total valgt uke</span>
                <strong>{escape(fmt_amount(week_total))}</strong>
            </article>
            <article class="sun">
                <span>Soling</span>
                <strong>{escape(fmt_amount(week_sol))}</strong>
                <small>{escape(share_text(week_sol))}</small>
            </article>
            <article class="parking">
                <span>Parkering</span>
                <strong>{escape(fmt_amount(week_parking))}</strong>
                <small>{escape(share_text(week_parking))}</small>
            </article>
        </div>
        <div class="revenue-bars">{"".join(bars)}</div>
        <div class="revenue-selected-day" aria-live="polite">
            <span>Valgt dag</span>
            <strong data-revenue-selected-label>{escape(selected['label'])}</strong>
            <div class="revenue-selected-grid">
                <article>
                    <span>Total</span>
                    <strong data-revenue-selected-total>{escape(selected['total'])}</strong>
                </article>
                <article class="sun">
                    <span>Soling</span>
                    <strong data-revenue-selected-sol>{escape(selected['sol'])}</strong>
                    <small data-revenue-selected-sol-count>{escape(selected['sol_count'])}</small>
                </article>
                <article class="parking">
                    <span>Parkering</span>
                    <strong data-revenue-selected-parking>{escape(selected['parking'])}</strong>
                    <small data-revenue-selected-parking-count>{escape(selected['parking_count'])}</small>
                </article>
            </div>
        </div>
    </section>
    <script>
    (() => {{
        const root = document.currentScript.previousElementSibling;
        const buttons = Array.from(root.querySelectorAll("[data-revenue-day]"));
        const fields = {{
            label: root.querySelector("[data-revenue-selected-label]"),
            total: root.querySelector("[data-revenue-selected-total]"),
            sol: root.querySelector("[data-revenue-selected-sol]"),
            solCount: root.querySelector("[data-revenue-selected-sol-count]"),
            parking: root.querySelector("[data-revenue-selected-parking]"),
            parkingCount: root.querySelector("[data-revenue-selected-parking-count]"),
        }};
        const selectDay = (button) => {{
            buttons.forEach((item) => {{
                const selected = item === button;
                item.classList.toggle("is-selected", selected);
                item.setAttribute("aria-pressed", selected ? "true" : "false");
            }});
            fields.label.textContent = button.dataset.label;
            fields.total.textContent = button.dataset.total;
            fields.sol.textContent = button.dataset.sol;
            fields.solCount.textContent = button.dataset.solCount;
            fields.parking.textContent = button.dataset.parking;
            fields.parkingCount.textContent = button.dataset.parkingCount;
        }};
        buttons.forEach((button) => button.addEventListener("click", () => selectDay(button)));
    }})();
    </script>
    """


METRIC_ICONS = {
    "sun": """
<svg class="metric-icon" viewBox="0 0 24 24" aria-hidden="true">
  <circle cx="12" cy="12" r="4.4"></circle>
  <path d="M12 2.8v2.2M12 19v2.2M4.1 4.1l1.6 1.6M18.3 18.3l1.6 1.6M2.8 12h2.2M19 12h2.2M4.1 19.9l1.6-1.6M18.3 5.7l1.6-1.6"></path>
</svg>
""",
    "parking": """
<svg class="metric-icon parking-icon" viewBox="0 0 24 24" aria-hidden="true">
  <path class="parking-mark" d="M6.1 21.2V7.9c0-3.3 2.2-5.5 5.5-5.5h4.2c3.5 0 6.1 2.6 6.1 6.1v4.5c0 3.5-2.6 6.1-6.1 6.1h-5.3v2.1a2.1 2.1 0 0 1-2.1 2.1H8.2a2.1 2.1 0 0 1-2.1-2.1z"></path>
  <path class="parking-cutout" d="M10.5 7.9h4.9c1.3 0 2.3 1 2.3 2.3v2.7c0 1.3-1 2.3-2.3 2.3h-4.6v-2.1l-6.1 3.9 6.1 3.9v-2.2h5.4c2.7 0 4.8-2.1 4.8-4.8V9.5c0-2.7-2.1-4.8-4.8-4.8h-5.7z"></path>
</svg>
""",
    "revenue": """
<svg class="metric-icon revenue-icon" viewBox="0 0 24 24" aria-hidden="true">
  <circle cx="12" cy="12" r="9.2"></circle>
  <path d="M7.2 5.9a7 7 0 0 0-1.9 4.3"></path>
  <path d="M6.4 18a7.1 7.1 0 0 0 3.2 1.8"></path>
  <path d="M17.4 6.6l.8.7"></path>
  <path d="M18.8 10.2h2.1"></path>
  <path d="M18.8 12.9h2.1"></path>
  <path d="M17.7 15.6h1.7"></path>
  <text x="12" y="14.75">kr</text>
</svg>
""",
    "chart": """
<svg class="metric-icon chart-icon" viewBox="0 0 24 24" aria-hidden="true">
  <path d="M3.5 19.5h17"></path>
  <path d="M4.2 16.5v-3.8"></path>
  <path d="M6.8 16.5V9.6"></path>
  <path d="M9.4 16.5v-5.4"></path>
  <path d="M12 16.5V5.8"></path>
  <path d="M14.6 16.5v-7.1"></path>
  <path d="M17.2 16.5v-4.8"></path>
  <path d="M19.8 16.5V7.4"></path>
</svg>
""",
    "energy": """
<svg class="metric-icon" viewBox="0 0 24 24" aria-hidden="true">
  <path d="M13.4 2.8 5.8 13h6.1l-1.3 8.2 7.6-10.3h-6.1z"></path>
</svg>
""",
    "temperature": """
<svg class="metric-icon" viewBox="0 0 24 24" aria-hidden="true">
  <path d="M10 14.6V5.5a3 3 0 0 1 6 0v9.1a4.8 4.8 0 1 1-6 0z"></path>
  <path d="M13 8.2v7.6"></path>
  <path d="M13 18.8h.01"></path>
</svg>
""",
    "door": """
<svg class="metric-icon" viewBox="0 0 24 24" aria-hidden="true">
  <path d="M7 21V4.5a1.7 1.7 0 0 1 1.7-1.7h7.6A1.7 1.7 0 0 1 18 4.5V21"></path>
  <path d="M5 21h15"></path>
  <path d="M14.3 12h.01"></path>
</svg>
""",
}


def metric_icon(name: str) -> str:
    return METRIC_ICONS.get(name, "")


def render_detail_page(title: str, subtitle: str, body: str, icon: str = "", hero_note: str = "") -> HTMLResponse:
    html = DETAIL_HTML
    detail_class = f"detail-{icon}" if icon else "detail-default"
    replacements = {
        "{{ title }}": escape(title),
        "{{ subtitle }}": escape(subtitle),
        "{{ body }}": body,
        "{{ detail_icon }}": metric_icon(icon),
        "{{ detail_class }}": detail_class,
        "{{ hero_note }}": hero_note,
    }
    for key, value in replacements.items():
        html = html.replace(key, value)
    return HTMLResponse(html)


LOGIN_HTML = """<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lilletorget online</title>
  <link rel="icon" type="image/png" href="/static/lilletorget-favicon.png">
  <link rel="stylesheet" href="/static/online-dashboard.css?v=1589">
</head>
<body class="login-page">
  <main class="login-shell">
    <section class="login-brand">
      <div class="brand-frame">
        <img src="/static/lilletorget-login.png" alt="Lilletorget solsenter og parkering">
      </div>
    </section>
    <section class="login-card">
      <p class="eyebrow">Lilletorget</p>
      <h1>Logg inn</h1>
      <p class="lead">Nøkkeltall for soling, parkering, lys og ventilasjon.</p>
      <form method="post" action="/auth/login">
        <label>Brukernavn<input name="username" autocomplete="username" placeholder="Skriv brukernavn" required></label>
        <label>Passord<input name="password" type="password" autocomplete="current-password" placeholder="Skriv passord" required></label>
        <button type="submit">Logg inn</button>
      </form>
      <p class="error">{{ error }}</p>
    </section>
  </main>
</body>
</html>"""


DASHBOARD_HTML = """<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="60">
  <title>Lilletorget nøkkeltall</title>
  <link rel="icon" type="image/png" href="/static/lilletorget-favicon.png">
  <link rel="stylesheet" href="/static/online-dashboard.css?v=1589">
</head>
<body>
  <header class="topbar">
    <a class="logo-link" href="/" aria-label="Til forsiden">
      <img src="/static/lilletorget-text.png" alt="Lilletorget">
    </a>
    <form method="post" action="/logg-ut">
      <button class="logout-button" type="submit" aria-label="Logg ut" title="Logg ut">
        <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
          <path d="M12 3v8" />
          <path d="M7.1 6.5a8 8 0 1 0 9.8 0" />
        </svg>
      </button>
    </form>
  </header>
  <main class="dashboard">
    <section class="pulse-grid">
      <article class="pulse-card accent-open">
        <span>Åpningstid</span>
        <strong>{{ open_label }}</strong>
        <small>{{ open_detail }}</small>
        <div class="progress"><i style="width: {{ open_progress }}%"></i></div>
      </article>
      <a class="pulse-card accent-energy card-link" href="/energi">
        <div class="metric-head"><span>Strøm nå</span>{{ energy_icon }}</div>
        <strong>{{ energy_watt }}</strong>
        <small>{{ energy_kwh }} i dag · {{ energy_samples }} målinger</small>
        <small class="updated-line">Diff {{ energy_diff }} · {{ energy_time }}</small>
      </a>
    </section>

    <section class="metric-grid">
      <a class="metric-card accent-sun card-link" href="/soling">
        <div class="metric-head"><span>Solinger</span>{{ sun_icon }}</div>
        <strong>{{ soling_count }}<em>/{{ soling_yesterday_count }}</em></strong>
        <small>I dag / i går</small>
        <small class="updated-line">Oppdatert {{ soling_time }}</small>
      </a>
      <a class="metric-card accent-parking card-link" href="/parkering">
        <div class="metric-head"><span>Parkering</span>{{ parking_icon }}</div>
        <strong>{{ parking_count }}<em>/{{ parking_yesterday_count }}</em></strong>
        <small>I dag / i går · {{ parking_active }} aktive</small>
        <small class="updated-line">Oppdatert {{ parking_time }}</small>
      </a>
      {{ revenue_card }}
    </section>

    <section class="temperature-grid">
      <a class="temperature-card temperature-mini card-link" href="/temperatur">
        <div class="temperature-main">
          <span>Inne</span>
          <strong>{{ inside_avg }}</strong>
        </div>
        <div class="temperature-list compact">
          <p><span>1.etg</span><strong>{{ temp_1etg }}</strong></p>
          <p><span>2.etg</span><strong>{{ temp_2etg }}</strong></p>
          <p><span>VIP</span><strong>{{ temp_vip }}</strong></p>
          <p><span>Fukt 1.etg</span><strong>{{ humidity_1etg }}</strong></p>
          <p><span>Fukt 2.etg</span><strong>{{ humidity_2etg }}</strong></p>
          <p><span>Fukt VIP</span><strong>{{ humidity_vip }}</strong></p>
          <p><span>Kjeller</span><strong>{{ temp_kjeller }}</strong></p>
          <p><span>Fukt</span><strong>{{ humidity_kjeller }}</strong></p>
        </div>
        <small class="card-time">Oppdatert {{ temp_time }}</small>
      </a>
      <a class="temperature-card temperature-mini card-link" href="/temperatur">
        <div class="temperature-main">
          <span>Ute</span>
          <strong>{{ outside }}</strong>
        </div>
        <div class="temperature-list compact">
          <p><span>Ute</span><strong>{{ outside_sensor }}</strong></p>
          <p><span>Fukt ute</span><strong>{{ humidity_ute }}</strong></p>
          <p><span>Innluft</span><strong>{{ innluft }}</strong></p>
          <p><span>Yr</span><strong>{{ yr_temp }}</strong></p>
          <p><span>Fukt Yr</span><strong>{{ humidity_yr }}</strong></p>
        </div>
        <small class="card-time">Oppdatert {{ temp_time }}</small>
      </a>
    </section>

    <a class="section-block card-link" href="/lys">
      <div class="section-title-row">
        <h2>LYS</h2>
        <div class="lux-pill"><span>Lux</span><strong>{{ lux }}</strong></div>
      </div>
      <div class="state-grid">{{ light_cards }}</div>
      <small class="card-time">Oppdatert {{ light_time }}</small>
    </a>

    <a class="section-block card-link" href="/ventilasjon">
      <div class="section-title-row">
        <h2>VENTILASJON</h2>
      </div>
      <div class="state-grid">{{ fan_cards }}</div>
      <small class="card-time">Oppdatert {{ temp_time }}</small>
    </a>

    <a class="section-block card-link solroom-doors-block" href="/solrom">
      <div class="section-title-row">
        <h2>SOLROM</h2>
        <span class="door-summary-pill">{{ solroom_door_summary }}</span>
      </div>
      {{ solroom_door_cards }}
    </a>

    <a class="section-block card-link door-alarm-block" href="/dorer/alarm">
      <div class="section-title-row">
        <h2>DØRALARM</h2>
        <span class="door-summary-pill">{{ door_alarm_summary }}</span>
      </div>
      {{ door_alarm_cards }}
    </a>

    <a class="section-block card-link other-doors-block" href="/dorer">
      <div class="section-title-row">
        <h2>ANDRE DØRER</h2>
        <span class="door-summary-pill">{{ other_door_summary }}</span>
      </div>
      {{ other_door_cards }}
    </a>
  </main>
</body>
</html>"""


DETAIL_HTML = """<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }} · Lilletorget</title>
  <link rel="icon" type="image/png" href="/static/lilletorget-favicon.png">
  <link rel="stylesheet" href="/static/online-dashboard.css?v=1589">
</head>
<body>
  <header class="topbar">
    <a class="logo-link" href="/" aria-label="Til forsiden">
      <img src="/static/lilletorget-text.png" alt="Lilletorget">
    </a>
    <form method="post" action="/logg-ut">
      <button class="logout-button" type="submit" aria-label="Logg ut" title="Logg ut">
        <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
          <path d="M12 3v8" />
          <path d="M7.1 6.5a8 8 0 1 0 9.8 0" />
        </svg>
      </button>
    </form>
  </header>
  <main class="dashboard detail-page {{ detail_class }}">
    <section class="detail-hero">
      <div class="detail-title">{{ detail_icon }}<h1>{{ title }}</h1></div>
      {{ hero_note }}
    </section>
    {{ body }}
  </main>
  <script>
    document.querySelectorAll(".detail-action").forEach((form) => {
      form.addEventListener("submit", () => {
        const button = form.querySelector("button");
        if (button) {
          button.textContent = "Oppdaterer...";
        }
      });
    });
  </script>
</body>
</html>"""
