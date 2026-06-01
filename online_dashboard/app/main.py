from datetime import date, datetime, timedelta
import hashlib
from html import escape
import asyncio
import json
import os
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

app = FastAPI(title="Lilletorget online", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


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


def easypark_period() -> tuple[date, date]:
    today = local_now().date()
    return today - timedelta(days=1), today


def easypark_downloader_request(path: str, params: dict[str, Any]) -> dict[str, Any]:
    query = urlencode({key: value for key, value in params.items() if value is not None})
    url = f"{EASYPARK_DOWNLOADER_URL}{path}"
    if query:
        url = f"{url}?{query}"
    request = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read().decode("utf-8", errors="replace")
    return json.loads(payload)


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
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    start, end = day_bounds(today)
    yesterday_start, yesterday_end = day_bounds(yesterday)
    last_week_same_day_start, last_week_same_day_end = day_bounds(last_week_same_day)
    week_start_dt = datetime.combine(week_start, datetime.min.time())
    month_start_dt = datetime.combine(month_start, datetime.min.time())

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
        select last_success_at as updated_at
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
    parking_import = await one_mapping(
        """
        select last_success_at as updated_at
        from import_job_status
        where job_name = 'easypark_parking_import'
        limit 1
        """
    )
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
    parking_week = await one_mapping(
        """
        select count(*) as count,
               coalesce(sum(fee_inc_vat), 0) as amount
        from parkering
        where start_time >= :start and start_time < :end
        """,
        {"start": week_start_dt, "end": end},
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

    return {
        "now": now,
        "open_state": operating_window(now),
        "soling": soling,
        "soling_yesterday": soling_yesterday,
        "soling_last_week_same_day": soling_last_week_same_day,
        "soling_week": soling_week,
        "soling_month": soling_month,
        "latest_soling": latest_soling,
        "session_import": session_import,
        "parking_import": parking_import,
        "parking": parking,
        "parking_yesterday": parking_yesterday,
        "parking_last_week_same_day": parking_last_week_same_day,
        "parking_week": parking_week,
        "parking_month": parking_month,
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
    html = DASHBOARD_HTML
    replacements = {
        "{{ user }}": user,
        "{{ now }}": data["now"].strftime("%d.%m.%Y %H:%M"),
        "{{ open_label }}": data["open_state"]["label"],
        "{{ open_detail }}": data["open_state"]["detail"],
        "{{ open_progress }}": str(data["open_state"]["progress"]),
        "{{ soling_count }}": fmt_int(data["soling"].get("count")),
        "{{ soling_yesterday_count }}": fmt_int(data["soling_yesterday"].get("count")),
        "{{ soling_amount }}": fmt_money(data["soling"].get("amount")),
        "{{ soling_minutes }}": f"{soling_hours:.1f} t".replace(".", ","),
        "{{ soling_compare }}": compare_text(data["soling"].get("count"), data["soling_yesterday"].get("count"), " stk"),
        "{{ soling_week_count }}": fmt_int(data["soling_week"].get("count")),
        "{{ soling_week_amount }}": fmt_money(data["soling_week"].get("amount")),
        "{{ soling_week_minutes }}": f"{week_soling_hours:.1f} t".replace(".", ","),
        "{{ soling_month_count }}": fmt_int(data["soling_month"].get("count")),
        "{{ soling_month_amount }}": fmt_money(data["soling_month"].get("amount")),
        "{{ latest_soling }}": latest_soling,
        "{{ soling_time }}": fmt_time(data["session_import"].get("updated_at")) if data["session_import"].get("updated_at") else fmt_time(data["soling"].get("updated_at")),
        "{{ parking_count }}": fmt_int(data["parking"].get("count")),
        "{{ parking_yesterday_count }}": fmt_int(data["parking_yesterday"].get("count")),
        "{{ parking_amount }}": fmt_money(data["parking"].get("amount")),
        "{{ parking_active }}": fmt_int(data["parking"].get("active_count")),
        "{{ parking_compare }}": compare_text(data["parking"].get("count"), data["parking_yesterday"].get("count"), " stk"),
        "{{ parking_week_count }}": fmt_int(data["parking_week"].get("count")),
        "{{ parking_week_amount }}": fmt_money(data["parking_week"].get("amount")),
        "{{ parking_month_count }}": fmt_int(data["parking_month"].get("count")),
        "{{ parking_month_amount }}": fmt_money(data["parking_month"].get("amount")),
        "{{ latest_parking }}": latest_parking,
        "{{ parking_time }}": fmt_time(data["parking_import"].get("updated_at")) if data["parking_import"].get("updated_at") else fmt_time(data["parking"].get("updated_at")),
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
    body = detail_stats(
        [
            ("I dag", fmt_int(data["soling"].get("count")), fmt_money(data["soling"].get("amount"))),
            (
                "Samme dag forrige uke",
                fmt_int(data["soling_last_week_same_day"].get("count")),
                fmt_money(data["soling_last_week_same_day"].get("amount")),
            ),
            ("Denne uken", fmt_int(data["soling_week"].get("count")), fmt_money(data["soling_week"].get("amount"))),
            ("Denne måneden", fmt_int(data["soling_month"].get("count")), fmt_money(data["soling_month"].get("amount"))),
        ]
    )
    body += render_list(
        "Siste solinger",
        [
            (
                fmt_time(row.get("started_at")),
                escape(str(row.get("room") or "Ukjent rom")),
                f"{float(row.get('duration_minutes') or 0):.0f} min · {fmt_money(row.get('paid_amount_kr'))}",
            )
            for row in rows
        ],
    )
    return render_detail_page("Soling", "Dagens solinger og utvikling hittil.", body)


@app.get("/parkering", response_class=HTMLResponse)
async def parking_detail(request: Request, refresh: Optional[str] = None):
    data = await dashboard_data()
    parking_import_at = data["parking_import"].get("updated_at")
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
    can_refresh = can_manage(request.state.access_key)
    from_day, to_day = easypark_period()
    refresh_label = {
        "ok": "Oppdatering startet/ferdig.",
        "busy": "EasyPark jobber allerede.",
        "denied": "Brukeren mangler driftstilgang.",
        "error": "Oppdatering feilet.",
    }.get(refresh or "", "")
    button = (
        f"""
        <form method="post" action="/parkering/oppdater" class="detail-action">
          <button type="submit">Oppdater dagens tall</button>
          <small>Henter EasyPark for {from_day.strftime('%d.%m')}-{to_day.strftime('%d.%m')}.</small>
        </form>
        """
        if can_refresh
        else '<p class="notice">Oppdatering krever master eller innstillingsbruker.</p>'
    )
    if refresh_label:
        button += f'<p class="notice">{escape(refresh_label)}</p>'
    body = detail_stats(
        [
            ("I dag", fmt_int(data["parking"].get("count")), fmt_money(data["parking"].get("amount"))),
            (
                "Samme dag forrige uke",
                fmt_int(data["parking_last_week_same_day"].get("count")),
                fmt_money(data["parking_last_week_same_day"].get("amount")),
            ),
            ("Aktive", fmt_int(data["parking"].get("active_count")), "nå"),
            ("Denne uken", fmt_int(data["parking_week"].get("count")), fmt_money(data["parking_week"].get("amount"))),
            ("Denne måneden", fmt_int(data["parking_month"].get("count")), fmt_money(data["parking_month"].get("amount"))),
            ("Siste EasyPark-import", fmt_date(parking_import_at), fmt_clock(parking_import_at)),
        ]
    )
    body += button
    body += render_list(
        "Siste parkeringer",
        [
            (
                fmt_time(row.get("start_time")),
                escape(str(row.get("car_license_number") or "Uten regnr")),
                f"{fmt_money(row.get('fee_inc_vat'))} · {float(row.get('parking_time_min') or 0):.0f} min",
            )
            for row in rows
        ],
    )
    return render_detail_page("Parkering", "Dagens parkeringer med trygg manuell oppdatering.", body)


@app.post("/parkering/oppdater")
async def parking_refresh(request: Request):
    if not can_manage(request.state.access_key):
        return RedirectResponse("/parkering?refresh=denied", status_code=303)
    from_day, to_day = easypark_period()
    try:
        result = await asyncio.to_thread(
            easypark_downloader_request,
            "/sync-period",
            {"from_date": from_day.isoformat(), "to_date": to_day.isoformat()},
        )
        status = result.get("status")
        outcome = "busy" if status == "busy" else "ok"
        if status == "error":
            outcome = "error"
    except Exception:
        outcome = "error"
    return RedirectResponse(f"/parkering?refresh={outcome}", status_code=303)


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
    return render_detail_page("Energi", "Strømstatus fra siste HC3-avlesning.", body)


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
    return render_detail_page("Temperatur", "Nåverdier og spenn hittil i dag.", body)


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
        cards.append(
            f"""
            <article>
                <span>{escape(label)}</span>
                <strong>{escape(value)}</strong>
                <small>{escape(subtext)}</small>
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
                <small>{detail}</small>
            </li>
            """
            for time_text, main, detail in rows
        )
    return f'<section class="section-block detail-list"><h2>{escape(title)}</h2><ul>{content}</ul></section>'


def render_detail_page(title: str, subtitle: str, body: str) -> HTMLResponse:
    html = DETAIL_HTML
    replacements = {
        "{{ title }}": escape(title),
        "{{ subtitle }}": escape(subtitle),
        "{{ body }}": body,
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
  <link rel="stylesheet" href="/static/online-dashboard.css">
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
  <link rel="stylesheet" href="/static/online-dashboard.css">
</head>
<body>
  <header class="topbar">
    <a class="logo-link" href="/" aria-label="Til forsiden">
      <img src="/static/lilletorget-text.png" alt="Lilletorget">
    </a>
    <form method="post" action="/logg-ut"><button type="submit">Logg ut</button></form>
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
        <span>Strøm nå</span>
        <strong>{{ energy_watt }}</strong>
        <small>{{ energy_kwh }} i dag · {{ energy_samples }} målinger</small>
        <small class="updated-line">Diff {{ energy_diff }} · {{ energy_time }}</small>
      </a>
    </section>

    <section class="metric-grid">
      <a class="metric-card accent-sun card-link" href="/soling">
        <span>Solinger</span>
        <strong>{{ soling_count }}<em>/{{ soling_yesterday_count }}</em></strong>
        <small>I dag / i går</small>
        <small class="updated-line">Oppdatert {{ soling_time }}</small>
      </a>
      <a class="metric-card accent-parking card-link" href="/parkering">
        <span>Parkering</span>
        <strong>{{ parking_count }}<em>/{{ parking_yesterday_count }}</em></strong>
        <small>I dag / i går · {{ parking_active }} aktive</small>
        <small class="updated-line">Oppdatert {{ parking_time }}</small>
      </a>
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
  <link rel="stylesheet" href="/static/online-dashboard.css">
</head>
<body>
  <header class="topbar">
    <a class="logo-link" href="/" aria-label="Til forsiden">
      <img src="/static/lilletorget-text.png" alt="Lilletorget">
    </a>
    <form method="post" action="/logg-ut"><button type="submit">Logg ut</button></form>
  </header>
  <main class="dashboard detail-page">
    <section class="detail-hero">
      <h1>{{ title }}</h1>
      <p>{{ subtitle }}</p>
    </section>
    {{ body }}
  </main>
</body>
</html>"""
