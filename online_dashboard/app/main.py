from datetime import date, datetime, timedelta
import hashlib
from html import escape
import os
from typing import Any, Optional
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


def fmt_time(value: Any) -> str:
    if not isinstance(value, datetime):
        return "-"
    return value.strftime("%d.%m %H:%M")


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


async def dashboard_data() -> dict[str, Any]:
    today = local_now().date()
    start, end = day_bounds(today)

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

    inside_values = [vent.get("temp_1etg"), vent.get("temp_2etg"), vent.get("temp_vip")]
    inside_values = [float(value) for value in inside_values if value is not None]
    inside_avg = vent.get("temp_avg_inne")
    if inside_avg is None and inside_values:
        inside_avg = sum(inside_values) / len(inside_values)

    outside = vent.get("temp_ute")
    if outside is None:
        outside = vent.get("temp_yr")

    return {
        "now": local_now(),
        "soling": soling,
        "session_import": session_import,
        "parking_import": parking_import,
        "parking": parking,
        "lights": lights,
        "vent": vent,
        "inside_avg": inside_avg,
        "outside": outside,
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
    html = DASHBOARD_HTML
    replacements = {
        "{{ user }}": user,
        "{{ now }}": data["now"].strftime("%d.%m.%Y %H:%M"),
        "{{ soling_count }}": fmt_int(data["soling"].get("count")),
        "{{ soling_amount }}": fmt_money(data["soling"].get("amount")),
        "{{ soling_minutes }}": f"{soling_hours:.1f} t".replace(".", ","),
        "{{ soling_time }}": fmt_time(data["session_import"].get("updated_at")) if data["session_import"].get("updated_at") else fmt_time(data["soling"].get("updated_at")),
        "{{ parking_count }}": fmt_int(data["parking"].get("count")),
        "{{ parking_amount }}": fmt_money(data["parking"].get("amount")),
        "{{ parking_active }}": fmt_int(data["parking"].get("active_count")),
        "{{ parking_time }}": fmt_time(data["parking_import"].get("updated_at")) if data["parking_import"].get("updated_at") else fmt_time(data["parking"].get("updated_at")),
        "{{ inside_avg }}": fmt_temp(data["inside_avg"]),
        "{{ outside }}": fmt_temp(data["outside"]),
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
    <img src="/static/lilletorget-text.png" alt="Lilletorget">
    <form method="post" action="/logg-ut"><button type="submit">Logg ut</button></form>
  </header>
  <main class="dashboard">
    <section class="metric-grid">
      <article class="metric-card accent-sun">
        <span>Solinger i dag</span>
        <strong>{{ soling_count }}</strong>
        <small>{{ soling_amount }} · {{ soling_minutes }}</small>
        <small class="updated-line">Oppdatert {{ soling_time }}</small>
      </article>
      <article class="metric-card accent-parking">
        <span>Parkering i dag</span>
        <strong>{{ parking_count }}</strong>
        <small>{{ parking_amount }} · {{ parking_active }} aktive</small>
        <small class="updated-line">Oppdatert {{ parking_time }}</small>
      </article>
    </section>

    <section class="temperature-card">
      <div class="temperature-main">
        <span>Inne</span>
        <strong>{{ inside_avg }}</strong>
      </div>
      <div class="temperature-list temperature-list-main">
        <p><span>1.etg</span><strong>{{ temp_1etg }}</strong></p>
        <p><span>2.etg</span><strong>{{ temp_2etg }}</strong></p>
        <p><span>VIP</span><strong>{{ temp_vip }}</strong></p>
      </div>
      <div class="temperature-list compact">
        <p><span>Ute</span><strong>{{ outside }}</strong></p>
        <p><span>Loft</span><strong>{{ loft }}</strong></p>
        <p><span>Innluft</span><strong>{{ innluft }}</strong></p>
      </div>
      <small class="card-time">Oppdatert {{ temp_time }}</small>
    </section>

    <section class="section-block">
      <div class="section-title-row">
        <h2>LYS</h2>
        <div class="lux-pill"><span>Lux</span><strong>{{ lux }}</strong></div>
      </div>
      <div class="state-grid">{{ light_cards }}</div>
      <small class="card-time">Oppdatert {{ light_time }}</small>
    </section>

    <section class="section-block">
      <div class="section-title-row">
        <h2>VENTILASJON</h2>
      </div>
      <div class="state-grid">{{ fan_cards }}</div>
      <small class="card-time">Oppdatert {{ temp_time }}</small>
    </section>
  </main>
</body>
</html>"""
