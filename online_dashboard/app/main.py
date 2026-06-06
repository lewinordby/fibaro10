from datetime import date, datetime, timedelta
import hashlib
from html import escape
import asyncio
import json
import os
import time
from typing import Any, Optional
from urllib.parse import urlencode
import urllib.request
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
LOCAL_TZ = ZoneInfo("Europe/Oslo")
AUTH_USER_COOKIE_NAME = "fibaro10_access_username"
AUTH_COOKIE_NAME = "fibaro10_access_password"
PUBLIC_PATHS = {"/health", "/favicon.ico", "/auth/login"}
PUBLIC_PREFIXES = ("/static/",)
ACCESS_FAILED_DISABLE_THRESHOLD = max(1, int(os.getenv("ACCESS_FAILED_DISABLE_THRESHOLD", "3")))
ONLINE_ACCESS_LOG_COOLDOWN_SECONDS = max(0, int(os.getenv("ONLINE_ACCESS_LOG_COOLDOWN_SECONDS", "0")))
EASYPARK_DOWNLOADER_URL = os.getenv("EASYPARK_DOWNLOADER_URL", "http://192.168.20.218:8109").rstrip("/")
EASYPARK_DOWNLOADER_TIMEOUT_SECONDS = max(60, int(os.getenv("EASYPARK_DOWNLOADER_TIMEOUT_SECONDS", "360")))
EASYPARK_REFRESH_RETRY_WAIT_SECONDS = max(0, int(os.getenv("EASYPARK_REFRESH_RETRY_WAIT_SECONDS", "30")))
PARKING_REFRESH_COOLDOWN_SECONDS = max(0, int(os.getenv("PARKING_REFRESH_COOLDOWN_SECONDS", "180")))

app = FastAPI(title="Lilletorget online", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)
parking_refresh_lock = asyncio.Lock()
parking_refresh_last_started_monotonic: Optional[float] = None


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


def easypark_downloader_request(path: str, params: dict[str, Any]) -> dict[str, Any]:
    query = urlencode({key: value for key, value in params.items() if value is not None})
    url = f"{EASYPARK_DOWNLOADER_URL}{path}"
    if query:
        url = f"{url}?{query}"
    request = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(request, timeout=EASYPARK_DOWNLOADER_TIMEOUT_SECONDS) as response:
        payload = response.read().decode("utf-8", errors="replace")
    return json.loads(payload)


def easypark_downloader_status() -> dict[str, Any]:
    try:
        with urllib.request.urlopen(f"{EASYPARK_DOWNLOADER_URL}/status", timeout=4) as response:
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


def import_run_rows(runs: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for run in runs:
        ok = run.get("ok")
        status = "OK" if ok is True else "Feil" if ok is False else str(run.get("status") or "-")
        imported = run.get("records_imported")
        total = run.get("records_total")
        if imported is not None and total is not None:
            records = f"{fmt_int(imported)} / {fmt_int(total)} rader"
        elif total is not None:
            records = f"{fmt_int(total)} rader"
        elif imported is not None:
            records = f"{fmt_int(imported)} rader"
        else:
            records = "Ingen radtall"
        message = short_message(run.get("message")) or "Ingen melding"
        stamp = run.get("finished_at") or run.get("started_at")
        return_time = fmt_time(stamp)
        rows.append((return_time, escape(status), escape(f"{records} · {message}")))
    return rows


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


async def dashboard_data() -> dict[str, Any]:
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
               temp_ute, temp_yr, temp_loft, temp_passiv, temp_luftinntak,
               fan_vip, fan_2etg, fan_tak
        from ventilasjon_samples
        order by bucket_start desc
        limit 1
        """
    )
    energy_now = await one_mapping(
        """
        select bucket_start, timestamp, inntak_w, belysning_w, varmepumper_w, differanse_beregnet_w
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
        ],
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


def render_login(error: str = "") -> HTMLResponse:
    return HTMLResponse(
        LOGIN_HTML.replace("{{ error }}", error),
        status_code=401 if error else 200,
    )


@app.get("/health")
async def health():
    return {"ok": True, "service": "online_dashboard"}


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
        "{{ innluft }}": fmt_temp(data["innluft"]),
        "{{ temp_1etg }}": fmt_temp(data["vent"].get("temp_1etg")),
        "{{ temp_2etg }}": fmt_temp(data["vent"].get("temp_2etg")),
        "{{ temp_vip }}": fmt_temp(data["vent"].get("temp_vip")),
        "{{ temp_time }}": fmt_time(data["vent"].get("bucket_start") or data["vent"].get("timestamp")),
        "{{ lux }}": fmt_int(data["lights"].get("lux")),
        "{{ light_time }}": fmt_time(data["lights"].get("bucket_start") or data["lights"].get("timestamp")),
    }
    for key, value in replacements.items():
        html = html.replace(key, value)
    html = html.replace("{{ light_cards }}", render_state_cards(data["light_items"], "light"))
    html = html.replace("{{ fan_cards }}", render_state_cards(data["fan_items"], "fan"))
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
    body += render_list(
        "Siste solinger",
        [
            (
                fmt_time(row.get("started_at")),
                escape(str(row.get("room") or "Ukjent rom")),
                f"{float(row.get('duration_minutes') or 0):.0f} min" + (f" - {amount(row.get('paid_amount_kr'))}" if can_view_money else ""),
            )
            for row in rows
        ],
    )
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
    week_rows = await revenue_week_data(week_start)
    body = render_revenue_week_chart_selectable(week_start, week_rows)
    updated_note = f'<p class="detail-hero-note">Sist oppdatert {fmt_clock(data["revenue_updated_at"])} {fmt_date(data["revenue_updated_at"])}</p>'
    return render_detail_page("Omsetning diagram", "Ukevis omsetning fra soling og parkering.", body, icon="revenue", hero_note=updated_note)


@app.get("/parkering", response_class=HTMLResponse)
async def parking_detail(request: Request, refresh: Optional[str] = None, reason: Optional[str] = None):
    data = await dashboard_data()
    can_view_money = can_manage(request.state.access_key)
    amount = lambda value: fmt_amount(value) if can_view_money else ""
    easypark_status = easypark_downloader_status()
    parking_import_at = data["parking_import"].get("updated_at")
    parking_failed_at = data["parking_import"].get("last_failed_at")
    import_status_text = f"Sist OK: {display_stamp(parking_import_at)}"
    if isinstance(parking_failed_at, datetime) and (not isinstance(parking_import_at, datetime) or parking_failed_at > parking_import_at):
        import_status_text = f"Siste forsøk feilet. Sist OK: {display_stamp(parking_import_at)}"
    start, end = day_bounds(data["now"].date())
    rows = await many_mappings(
        """
        select start_time, end_time, car_license_number, fee_inc_vat, parking_time_min, status
        from parkering
        where start_time >= :start and start_time < :end
        order by start_time desc
        limit 14
        """,
        {"start": start, "end": end},
    )
    import_runs = await many_mappings(
        """
        select finished_at, started_at, ok, status, records_imported, records_total, message
        from import_job_runs
        where job_name = 'easypark_parking_import'
        order by finished_at desc nulls last, id desc
        limit 5
        """
    )
    can_refresh = can_manage(request.state.access_key)
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
            ("I går", fmt_int(data["parking_yesterday"].get("count")), amount(data["parking_yesterday"].get("amount"))),
            (
                "I dag",
                fmt_int(data["parking"].get("count")),
                parking_today_detail,
            ),
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
    body += f'<p class="detail-updated-line">Sist oppdatert {fmt_clock(parking_import_at)} {fmt_date(parking_import_at)}</p>'
    body += button
    body += render_list("Siste importforsøk", import_run_rows(import_runs))
    body += render_list(
        "Siste parkeringer",
        [
            (
                fmt_time(row.get("start_time")),
                escape(str(row.get("car_license_number") or "Uten regnr")),
                (f"{amount(row.get('fee_inc_vat'))} - " if can_view_money else "") + f"{float(row.get('parking_time_min') or 0):.0f} min",
            )
            for row in rows
        ],
    )
    return render_detail_page("Parkering", "Dagens parkeringer med trygg manuell oppdatering.", body, icon="parking")


@app.post("/parkering/oppdater")
async def parking_refresh(request: Request):
    global parking_refresh_last_started_monotonic
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
                    "/sync-period",
                    {"from_date": from_day.isoformat(), "to_date": to_day.isoformat()},
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
        ]
    )
    body += f'<p class="notice">Beregnet differanse akkurat nå: <strong>{fmt_watt(now.get("differanse_beregnet_w"))}</strong>.</p>'
    return render_detail_page("Energi", "Strømstatus fra siste HC3-avlesning.", body, icon="energy")


@app.get("/temperatur", response_class=HTMLResponse)
async def temperature_detail(request: Request):
    data = await dashboard_data()
    start, end = day_bounds(data["now"].date())
    ranges = await one_mapping(
        """
        select min(temp_avg_inne) as min_inne, max(temp_avg_inne) as max_inne,
               min(temp_ute) as min_ute, max(temp_ute) as max_ute,
               min(temp_loft) as min_loft, max(temp_loft) as max_loft
        from ventilasjon_samples
        where bucket_start >= :start and bucket_start < :end
        """,
        {"start": start, "end": end},
    )
    body = detail_stats(
        [
            ("Inne nå", fmt_temp(data["inside_avg"]), f"{fmt_temp(ranges.get('min_inne'))} - {fmt_temp(ranges.get('max_inne'))}"),
            ("Ute nå", fmt_temp(data["outside"]), f"{fmt_temp(ranges.get('min_ute'))} - {fmt_temp(ranges.get('max_ute'))}"),
            ("Loft nå", fmt_temp(data["vent"].get("temp_loft")), f"{fmt_temp(ranges.get('min_loft'))} - {fmt_temp(ranges.get('max_loft'))}"),
            ("Innluft", fmt_temp(data["innluft"]), f"Oppdatert {fmt_time(data['vent'].get('bucket_start') or data['vent'].get('timestamp'))}"),
        ]
    )
    return render_detail_page("Temperatur", "Nåverdier og spenn hittil i dag.", body, icon="temperature")


@app.get("/lys", response_class=HTMLResponse)
async def light_detail(request: Request):
    data = await dashboard_data()
    events = await many_mappings(
        """
        select timestamp, device_name, action, lux, reason
        from utelys_events
        order by timestamp desc
        limit 10
        """
    )
    body = f'<section class="section-block"><div class="section-title-row"><h2>LYS</h2><div class="lux-pill"><span>Lux</span><strong>{fmt_int(data["lights"].get("lux"))}</strong></div></div><div class="state-grid">{render_state_cards(data["light_items"], "light")}</div><small class="card-time">Oppdatert {fmt_time(data["lights"].get("bucket_start") or data["lights"].get("timestamp"))}</small></section>'
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
    events = await many_mappings(
        """
        select timestamp, device_name, action, mode, reason
        from ventilasjon_events
        order by timestamp desc
        limit 10
        """
    )
    body = f'<section class="section-block"><div class="section-title-row"><h2>VENTILASJON</h2></div><div class="state-grid">{render_state_cards(data["fan_items"], "fan")}</div><small class="card-time">Oppdatert {fmt_time(data["vent"].get("bucket_start") or data["vent"].get("timestamp"))}</small></section>'
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
  <link rel="stylesheet" href="/static/online-dashboard.css?v=20260605-revenue-chart-spaced-2">
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
  <link rel="stylesheet" href="/static/online-dashboard.css?v=20260605-revenue-chart-spaced-2">
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
          <p><span>Innluft</span><strong>{{ innluft }}</strong></p>
          <p><span>Yr</span><strong>{{ yr_temp }}</strong></p>
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
  <link rel="stylesheet" href="/static/online-dashboard.css?v=20260605-revenue-chart-spaced-2">
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
