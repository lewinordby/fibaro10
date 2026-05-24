from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from playwright.sync_api import TimeoutError as PwTimeoutError
from playwright.sync_api import sync_playwright

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


load_dotenv()


def env_value(name: str, default: str | None = None) -> str | None:
    return os.getenv(name) or os.getenv(name.lower()) or default


def env_required(name: str) -> str:
    value = (env_value(name, "") or "").strip()
    if not value:
        raise RuntimeError(f"Mangler env var: {name}")
    return value


def timezone_name() -> str:
    return env_value("TZ", "Europe/Oslo") or "Europe/Oslo"


def local_now() -> datetime:
    if ZoneInfo is None:
        return datetime.now()
    try:
        return datetime.now(ZoneInfo(timezone_name()))
    except Exception:
        return datetime.now()


def local_today() -> date:
    return local_now().date()


BASE_URL = env_value("BASE_URL", "https://sun2owner.repayal.com") or "https://sun2owner.repayal.com"
LIST_URL = (env_value("LIST_URL", "") or "").strip()
NAVIGATION_LABELS = [part.strip() for part in (env_value("NAVIGATION_LABELS", "Statistikk|Bruker|Liste") or "").split("|") if part.strip()]
MEMBERS_URL = (env_value("MEMBERS_URL", "") or "").strip()
MEMBER_NAVIGATION_LABELS = [part.strip() for part in (env_value("MEMBER_NAVIGATION_LABELS", "Medlemmer|Brukere|Kunder") or "").split("|") if part.strip()]
OUT_DIR = Path(env_value("OUT_DIR", "/data/session_exports") or "/data/session_exports")
ERROR_DIR = Path(env_value("ERROR_DIR", "/data/session_errors") or "/data/session_errors")
STATUS_FILE = Path(env_value("STATUS_FILE", "/data/session_scraper_status.json") or "/data/session_scraper_status.json")
PAUSE_SECONDS = float(env_value("PAUSE_SECONDS", "2") or "2")
SKIP_EXISTING = (env_value("SKIP_EXISTING", "1") or "1") == "1"
AUTO_START = (env_value("AUTO_START", "0") or "0") == "1"
SCHEDULE_ENABLED = (env_value("SCHEDULE_ENABLED", "1") or "1") == "1"
SCHEDULE_POLL_SECONDS = int(env_value("SCHEDULE_POLL_SECONDS", "60") or "60")
SCHEDULE_SESSIONS_TIME = env_value("SCHEDULE_SESSIONS_TIME", "02:10") or "02:10"
SCHEDULE_BEDS_TIME = env_value("SCHEDULE_BEDS_TIME", "02:40") or "02:40"
SCHEDULE_MEMBERS_TIME = env_value("SCHEDULE_MEMBERS_TIME", "03:10") or "03:10"
POST_TO_FIBARO10 = (env_value("POST_TO_FIBARO10", "0") or "0") == "1"
FIBARO10_API_BASE_URL = (env_value("FIBARO10_API_BASE_URL", "https://fibaro10.onrender.com") or "").rstrip("/")
FIBARO10_API_USERNAME = env_value("FIBARO10_API_USERNAME", "") or ""
FIBARO10_API_PASSWORD = env_value("FIBARO10_API_PASSWORD", "") or ""
COLLECTOR_ID = env_value("COLLECTOR_ID", "qnap-sun2-session-scraper") or "qnap-sun2-session-scraper"
MEMBER_PROFILE_LIMIT = int(env_value("MEMBER_PROFILE_LIMIT", "120") or "120")
FETCH_MEMBER_PROFILES = (env_value("FETCH_MEMBER_PROFILES", "1") or "1") == "1"
MEMBER_POST_BATCH_SIZE = int(env_value("MEMBER_POST_BATCH_SIZE", "500") or "500")

app = FastAPI(title="Sun2_session_scraper")
task: asyncio.Task | None = None
scheduler_task: asyncio.Task | None = None
schedule_lock = asyncio.Lock()
stop_requested = False

state: dict[str, Any] = {
    "started_at": datetime.utcnow().isoformat(),
    "running": False,
    "stop_requested": False,
    "last_error": None,
    "last_action": None,
    "last_period": None,
    "last_success_period": None,
    "last_success_at": None,
    "created_files": 0,
    "posted_files": 0,
    "skipped_files": 0,
    "failed": 0,
    "rows_last_file": 0,
    "beds_last_sync": None,
    "beds_last_count": 0,
    "members_last_sync": None,
    "members_last_count": 0,
    "members_last_named_count": 0,
    "scheduler_enabled": SCHEDULE_ENABLED,
    "scheduler_last_check": None,
    "scheduler_last_action": None,
    "scheduled_last_runs": {},
    "current_file": None,
    "range": {},
}


def normalize_schedule_time(value: str, default: str) -> str:
    try:
        hour_text, minute_text = value.strip().split(":", 1)
        hour = max(0, min(23, int(hour_text)))
        minute = max(0, min(59, int(minute_text)))
        return f"{hour:02d}:{minute:02d}"
    except Exception:
        return default


def schedule_due(job_key: str, time_text: str, now: datetime) -> bool:
    scheduled = normalize_schedule_time(time_text, "02:00")
    last_runs = state.setdefault("scheduled_last_runs", {})
    return now.strftime("%H:%M") >= scheduled and last_runs.get(job_key) != now.date().isoformat()


def mark_scheduled_attempt(job_key: str, now: datetime) -> None:
    last_runs = state.setdefault("scheduled_last_runs", {})
    last_runs[job_key] = now.date().isoformat()
    state["scheduler_last_action"] = f"{job_key} {now:%Y-%m-%d %H:%M:%S}"


def parse_date(value: str | None, default: date) -> date:
    if not value:
        return default
    return date.fromisoformat(value.strip())


def month_start(day: date) -> date:
    return day.replace(day=1)


def next_month(day: date) -> date:
    return (day.replace(day=28) + timedelta(days=4)).replace(day=1)


def month_end(day: date) -> date:
    return next_month(day) - timedelta(days=1)


def iter_month_ranges(start: date, end: date):
    current = month_start(start)
    while current <= end:
        yield max(start, current), min(end, month_end(current))
        current = next_month(current)


def filename_for(start: date) -> str:
    return f"Sun2_sessions_{start:%Y-%m}.json"


def load_progress() -> dict[str, Any]:
    if not STATUS_FILE.exists():
        return {}
    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_progress(extra: dict[str, Any]) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {**state, **extra, "saved_at": datetime.utcnow().isoformat()}
    STATUS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def normalize_text(value: Any) -> str:
    text = str(value or "").replace("\xa0", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_key(value: Any) -> str:
    text = normalize_text(value).lower()
    replacements = str.maketrans({
        "\u00e6": "a",
        "\u00f8": "o",
        "\u00e5": "a",
        "\u00e4": "a",
        "\u00f6": "o",
        "\u00fc": "u",
        "\u00e9": "e",
        "\u00e8": "e",
    })
    return re.sub(r"[^a-z0-9]+", "_", text.translate(replacements)).strip("_")


def parse_number(value: Any) -> float | None:
    text = normalize_text(value)
    if not text:
        return None
    match = re.search(r"-?\d+(?:[.,]\d+)?", text.replace(" ", ""))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def parse_duration_minutes(value: Any) -> float | None:
    text = normalize_text(value).lower()
    if not text:
        return None
    hours = 0.0
    minutes = 0.0
    hour_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:time|timer|t)\b", text)
    minute_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:minutt|minutter|min)\b", text)
    if hour_match:
        hours = float(hour_match.group(1).replace(",", "."))
    if minute_match:
        minutes = float(minute_match.group(1).replace(",", "."))
    if hour_match or minute_match:
        return hours * 60 + minutes
    return parse_number(text)


def decode_sun2_member_token(token: Any) -> tuple[str | None, str | None]:
    text = normalize_text(token)
    if not text or "." not in text:
        return None, None
    try:
        payload = text.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode()).decode("utf-8", errors="ignore").strip().strip('"')
    except Exception:
        return None, None
    match = re.match(r"(\d+)-(\d+)", decoded)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def decode_sun2_pk_token(token: Any) -> tuple[str | None, str | None]:
    return decode_sun2_member_token(token)


def parse_datetime_guess(value: Any, fallback_day: date) -> datetime | None:
    text = normalize_text(value)
    if not text:
        return None
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            pass
    match = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2}).*?(\d{1,2}):(\d{2})", text)
    if match:
        year, month, day, hour, minute = [int(part) for part in match.groups()]
        return datetime(year, month, day, hour, minute)
    match = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4}).*?(\d{1,2}):(\d{2})", text)
    if match:
        day, month, year, hour, minute = [int(part) for part in match.groups()]
        if year < 100:
            year += 2000
        return datetime(year, month, day, hour, minute)
    match = re.search(r"(\d{1,2}):(\d{2})", text)
    if match:
        hour, minute = [int(part) for part in match.groups()]
        return datetime(fallback_day.year, fallback_day.month, fallback_day.day, hour, minute)
    return None


def parse_date_guess(value: Any) -> date | None:
    text = normalize_text(value)
    if not text:
        return None
    for pattern in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            pass
    match = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", text)
    if match:
        day, month, year = [int(part) for part in match.groups()]
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            return None
    match = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", text)
    if match:
        year, month, day = [int(part) for part in match.groups()]
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def parse_int(value: Any) -> int | None:
    number = parse_number(value)
    return int(number) if number is not None else None


def pick(row: dict[str, str], *keywords: str) -> str:
    normalized_keywords = [normalize_key(keyword) for keyword in keywords]
    for key, value in row.items():
        nkey = normalize_key(key)
        if any(keyword in nkey for keyword in normalized_keywords):
            return value
    return ""


def pick_identifier(row: dict[str, str]) -> str:
    exact_keys = {"id", "nr", "nummer", "ordre_id", "booking_id", "transaksjon_id", "kvittering"}
    for key, value in row.items():
        if normalize_key(key) in exact_keys:
            return value
    return pick(row, "ordre", "transaksjon", "booking", "kvittering", "session")


def row_hash(row: dict[str, Any]) -> str:
    data = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(data.encode("utf-8")).hexdigest()


def room_key_from_name(value: str) -> str:
    text = normalize_text(value)
    match = re.search(r"\brom\s*0*(\d+)\b", text, re.IGNORECASE)
    if match:
        return f"rom_{int(match.group(1)):02d}"
    return normalize_key(text) or "ukjent_rom"


SUN2_ROOM_MAP_BY_DISPLAY = {
    1: {"room_id": "rom-01", "physical_room_number": 1, "display_room_number": 1, "sun2_bed_id": "640"},
    2: {"room_id": "rom-02", "physical_room_number": 2, "display_room_number": 2, "sun2_bed_id": "641"},
    3: {"room_id": "rom-03", "physical_room_number": 3, "display_room_number": 3, "sun2_bed_id": "642"},
    4: {"room_id": "rom-04", "physical_room_number": 4, "display_room_number": 4, "sun2_bed_id": "643"},
    5: {"room_id": "rom-05", "physical_room_number": 5, "display_room_number": 5, "sun2_bed_id": "644"},
    6: {"room_id": "rom-06", "physical_room_number": 6, "display_room_number": 6, "sun2_bed_id": "645"},
    7: {"room_id": "rom-07", "physical_room_number": 7, "display_room_number": 7, "sun2_bed_id": "646"},
    8: {"room_id": "rom-08", "physical_room_number": 8, "display_room_number": 8, "sun2_bed_id": "647"},
    9: {"room_id": "rom-09", "physical_room_number": 9, "display_room_number": 9, "sun2_bed_id": "648"},
    10: {"room_id": "rom-11", "physical_room_number": 11, "display_room_number": 10, "sun2_bed_id": "679"},
    11: {"room_id": "rom-12", "physical_room_number": 12, "display_room_number": 11, "sun2_bed_id": "680"},
    12: {"room_id": "rom-13", "physical_room_number": 13, "display_room_number": 12, "sun2_bed_id": "681"},
}

SUN2_ROOM_UNKNOWN_OLD_10 = {"room_id": "rom-10", "physical_room_number": 10, "display_room_number": None, "sun2_bed_id": "649"}


def room_identity(value: Any, bed_id: str | None = None) -> dict[str, Any]:
    text = normalize_text(value)
    bed_id = normalize_text(bed_id)
    if text in {".", "-", ""}:
        result = dict(SUN2_ROOM_UNKNOWN_OLD_10)
    else:
        match = re.search(r"\brom\s*0*(\d{1,2})\b", text, re.IGNORECASE)
        result = dict(SUN2_ROOM_MAP_BY_DISPLAY.get(int(match.group(1)), {})) if match else {}
    if bed_id:
        result["sun2_bed_id"] = bed_id
    return result


def normalize_session_row(raw: dict[str, str], fallback_day: date) -> dict[str, Any] | None:
    started_text = pick(raw, "start", "tidspunkt", "dato", "siste soling", "time")
    if not started_text:
        started_text = next((value for value in raw.values() if parse_datetime_guess(value, fallback_day)), "")
    started_at = parse_datetime_guess(started_text, fallback_day)
    if not started_at:
        return None

    duration = parse_duration_minutes(pick(raw, "varighet", "soletid", "soltid", "minutter", "min"))
    paid = parse_number(pick(raw, "kostnad", "betalt", "pris", "belop", "inntjent", "kr"))
    room = pick(raw, "rom", "seng", "bed", "solarium")
    identity = room_identity(room)
    user_name = pick(raw, "bruker", "kunde", "navn", "medlem") or normalize_text(raw.get("__user_title"))
    user_identifier = pick(raw, "kunde id", "bruker id", "medlemsnummer", "telefon", "epost", "email")
    payment_method = pick(raw, "betalingsmiddel", "betaling", "payment")
    status = pick(raw, "status", "resultat") or payment_method
    customer_type = pick(raw, "kundetype", "type", "medlemstype")
    gender = pick(raw, "kjonn", "kjønn", "gender")
    sun2_user_id = normalize_text(raw.get("__sun2_user_id"))
    sun2_center_id = normalize_text(raw.get("__sun2_center_id"))
    token_center_id, token_user_id = decode_sun2_member_token(raw.get("__sun2_user_token"))
    if not sun2_center_id:
        sun2_center_id = token_center_id or ""
    if not sun2_user_id:
        sun2_user_id = token_user_id or ""
    ended_at = None
    if duration is not None:
        ended_at = started_at + timedelta(minutes=duration)

    source_id = pick_identifier(raw)
    if not source_id:
        source_id = row_hash({"started_at": started_at.isoformat(), "room": room, "user": user_name, "duration": duration, "paid": paid, "raw": raw})
    raw_for_storage = {key: value for key, value in raw.items() if key not in {"__sun2_user_token", "__user_href"}}

    return {
        "source_session_id": normalize_text(source_id),
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat() if ended_at else None,
        "stat_date": started_at.date().isoformat(),
        "room_id": identity.get("room_id"),
        "room": normalize_text(room) or None,
        "room_key": room_key_from_name(room) if room else None,
        "source_room_name": normalize_text(room) or None,
        "sun2_bed_id": identity.get("sun2_bed_id"),
        "sun2_user_id": sun2_user_id or None,
        "sun2_center_id": sun2_center_id or None,
        "user_name": normalize_text(user_name) or None,
        "user_identifier": normalize_text(user_identifier) or None,
        "customer_type": normalize_text(customer_type) or None,
        "gender": normalize_text(gender) or None,
        "payment_method": normalize_text(payment_method) or None,
        "duration_minutes": duration,
        "paid_amount_kr": paid,
        "status": normalize_text(status) or None,
        "raw": raw_for_storage,
    }


def login_if_needed(page, username: str, password: str) -> None:
    if page.locator("#password").count() == 0 and page.locator("input[type='password']").count() == 0:
        return
    if page.locator("#username").count() > 0:
        page.locator("#username").fill(username)
    else:
        page.locator("input[name='username'], input[type='text'], input[type='email']").first.fill(username)
    if page.locator("#password").count() > 0:
        page.locator("#password").fill(password)
    else:
        page.locator("input[name='password'], input[type='password']").first.fill(password)
    if page.locator("#login-action").count() > 0:
        page.locator("#login-action").click()
    elif page.get_by_text("Logg inn").count() > 0:
        page.get_by_text("Logg inn").first.click()
    else:
        page.locator("button[type='submit'], input[type='submit']").first.click()
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PwTimeoutError:
        pass


def click_text_if_present(page, text: str) -> bool:
    candidates = [
        page.get_by_role("link", name=re.compile(re.escape(text), re.I)),
        page.get_by_role("button", name=re.compile(re.escape(text), re.I)),
        page.get_by_text(re.compile(re.escape(text), re.I)),
    ]
    for candidate in candidates:
        try:
            if candidate.count() > 0:
                candidate.first.click(timeout=5000)
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except PwTimeoutError:
                    pass
                return True
        except Exception:
            continue
    return False


def open_sessions_page(page, username: str, password: str) -> None:
    page.goto(LIST_URL or BASE_URL, wait_until="domcontentloaded")
    login_if_needed(page, username, password)
    if LIST_URL:
        return
    for label in NAVIGATION_LABELS:
        click_text_if_present(page, label)


def open_beds_page(page, username: str, password: str) -> None:
    page.goto(BASE_URL, wait_until="domcontentloaded")
    login_if_needed(page, username, password)
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except PwTimeoutError:
        pass
    page.goto(f"{BASE_URL.rstrip('/')}/settings_beds.php", wait_until="domcontentloaded")
    login_if_needed(page, username, password)
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except PwTimeoutError:
        pass
    page.wait_for_timeout(750)


def open_members_page(page, username: str, password: str) -> None:
    page.goto(MEMBERS_URL or BASE_URL, wait_until="domcontentloaded")
    login_if_needed(page, username, password)
    if MEMBERS_URL:
        return
    member_href = ""
    try:
        member_href = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('a'))
              .map(a => a.href || '')
              .find(href => href.includes('members_show.php')) || ''
            """
        )
    except Exception:
        member_href = ""
    if member_href:
        page.goto(member_href, wait_until="domcontentloaded")
        login_if_needed(page, username, password)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except PwTimeoutError:
            pass
        page.wait_for_timeout(750)
        return
    for label in MEMBER_NAVIGATION_LABELS:
        click_text_if_present(page, label)
    page.wait_for_timeout(750)


def absolute_url(value: Any) -> str:
    text = normalize_text(value)
    if not text or text == "#":
        return ""
    return urljoin(BASE_URL.rstrip("/") + "/", text)


def profile_pairs_from_page(page) -> dict[str, str]:
    try:
        return page.evaluate(
            """
            () => {
              const norm = (text) => String(text || '').replace(/\\s+/g, ' ').trim();
              const pairs = {};
              const add = (key, value) => {
                key = norm(key).replace(/:$/, '');
                value = norm(value);
                if (key && value && !pairs[key]) pairs[key] = value;
              };
              document.querySelectorAll('tr').forEach(tr => {
                const cells = Array.from(tr.children).map(td => norm(td.innerText || td.textContent));
                if (cells.length >= 2) add(cells[0], cells.slice(1).join(' '));
              });
              document.querySelectorAll('dt').forEach(dt => add(dt.innerText, dt.nextElementSibling ? dt.nextElementSibling.innerText : ''));
              document.querySelectorAll('input, select, textarea').forEach(el => {
                const id = el.getAttribute('id') || '';
                const name = el.getAttribute('name') || '';
                const label = id ? document.querySelector(`label[for="${CSS.escape(id)}"]`) : null;
                const key = (label && label.innerText) || el.getAttribute('placeholder') || name || id;
                const value = el.tagName === 'SELECT'
                  ? (el.options[el.selectedIndex]?.text || el.value || '')
                  : (el.value || el.getAttribute('value') || '');
                add(key, value);
              });
              return pairs;
            }
            """
        ) or {}
    except Exception:
        return {}


def extract_age(value: Any) -> int | None:
    text = normalize_text(value)
    match = re.search(r"\((\d{1,3})\s*år\)", text, re.I)
    if not match:
        match = re.search(r"\b(\d{1,3})\s*år\b", text, re.I)
    return int(match.group(1)) if match else None


def looks_like_initials(value: Any) -> bool:
    text = re.sub(r"\([^)]*\)", "", normalize_text(value)).strip()
    if not text:
        return False
    parts = text.split()
    return 1 <= len(parts) <= 4 and all(re.fullmatch(r"[A-Za-zÆØÅæøå]\.?", part) for part in parts)


def normalize_member_row(raw: dict[str, str], profile: dict[str, str] | None = None) -> dict[str, Any] | None:
    merged = {**raw, **(profile or {})}
    sun2_user_id = normalize_text(raw.get("__sun2_user_id"))
    sun2_center_id = normalize_text(raw.get("__sun2_center_id"))
    token_center_id, token_user_id = decode_sun2_member_token(raw.get("__sun2_user_token"))
    if not sun2_center_id:
        sun2_center_id = token_center_id or ""
    if not sun2_user_id:
        sun2_user_id = token_user_id or ""
    if not sun2_user_id:
        sun2_user_id = normalize_text(pick(merged, "sun2 id", "bruker id", "kunde id", "medlemsnummer", "id"))
    if not sun2_user_id:
        return None

    display_name = normalize_text(
        pick(merged, "fullt navn", "navn", "bruker", "kunde", "medlem") or raw.get("__user_title")
    )
    display_name = re.sub(r"^ID#\s*\d+\s*", "", display_name, flags=re.I).strip()
    full_name = normalize_text(pick(profile or {}, "fullt navn", "navn", "fornavn")) if profile else ""
    if not full_name and display_name and not looks_like_initials(display_name):
        full_name = display_name
    initials = normalize_text(raw.get("__user_title") or display_name)
    if not looks_like_initials(initials):
        initials = ""
    age = extract_age(display_name) or extract_age(pick(merged, "alder"))
    email = normalize_text(pick(merged, "epost", "e-post", "email", "mail"))
    phone = normalize_text(pick(merged, "telefon", "mobil", "phone"))
    birth_date = parse_date_guess(pick(merged, "fødselsdato", "fodselsdato", "født", "fodsels"))
    member_since = parse_date_guess(pick(merged, "ble medlem", "medlem siden", "opprettet", "registrert"))
    last_seen = parse_datetime_guess(pick(merged, "sist aktiv", "siste soling", "sist besøk", "sist brukt"), local_today())
    raw_for_storage = {
        key: value
        for key, value in raw.items()
        if key not in {"__sun2_user_token"}
    }
    if profile:
        raw_for_storage["profile"] = profile
    return {
        "sun2_user_id": sun2_user_id,
        "sun2_center_id": sun2_center_id or None,
        "name": full_name or None,
        "display_name": display_name or full_name or initials or None,
        "initials": initials or None,
        "age": age,
        "email": email or None,
        "phone": phone or None,
        "profile_url": absolute_url(raw.get("__user_href")) or None,
        "customer_type": normalize_text(pick(merged, "kundetype", "medlemstype", "type")) or None,
        "gender": normalize_text(pick(merged, "kjønn", "kjonn", "gender")) or None,
        "birth_date": birth_date.isoformat() if birth_date else None,
        "member_since": member_since.isoformat() if member_since else None,
        "last_seen_at": last_seen.isoformat() if last_seen else None,
        "status": normalize_text(pick(merged, "status")) or None,
        "balance_kr": parse_number(pick(merged, "saldo", "balanse")),
        "total_spent_kr": parse_number(pick(merged, "totalt", "omsetning", "kjøpt", "brukt")),
        "visits_count": parse_int(pick(merged, "solinger", "besøk", "antall")),
        "raw": raw_for_storage,
    }


def extract_beds(page) -> list[dict[str, Any]]:
    rows = page.evaluate(
        """
        () => Array.from(document.querySelectorAll('.tile-stats')).map((row) => {
          const text = (selector) => {
            const item = row.querySelector(selector);
            return item ? (item.innerText || item.textContent || '').trim() : '';
          };
          const attr = (selector, name) => {
            const item = row.querySelector(selector);
            return item ? (item.getAttribute(name) || '') : '';
          };
          const name = text('.settings-bed-names');
          if (!name) return null;
          const lamps = Array.from(row.querySelectorAll('.settings-bed-lamp-info')).map((item) => (
            item.getAttribute('title') || item.innerText || item.textContent || ''
          ).trim()).filter(Boolean);
          return {
            name,
            name_token: attr('.settings-bed-names', 'data-pk'),
            bed_model: text('.settings-bed-types'),
            bed_model_id: attr('.settings-bed-types', 'data-value') || attr('.settings-bed-types', 'data-pk'),
            max_minutes: text('.settings-bed-max-time'),
            startup_minutes: text('.settings-bed-startup-time'),
            cooldown_minutes: text('.settings-bed-aftercooling-time') || text('.settings-bed-after-cooling-time') || text('.settings-bed-cooldown-time'),
            current_price_per_min: text('.settings-bed-prices'),
            status: text('.settings-bed-statuses'),
            status_code: attr('.settings-bed-statuses', 'data-value'),
            lamp_status: lamps.join(' | ')
          };
        }).filter(Boolean)
        """
    )
    beds: list[dict[str, Any]] = []
    for raw in rows:
        center_id, bed_id = decode_sun2_pk_token(raw.get("name_token"))
        if not bed_id:
            continue
        name = normalize_text(raw.get("name"))
        identity = room_identity(name, bed_id)
        beds.append(
            {
                "room_id": identity.get("room_id"),
                "physical_room_number": identity.get("physical_room_number"),
                "display_room_number": identity.get("display_room_number"),
                "sun2_center_id": center_id,
                "sun2_bed_id": bed_id,
                "name": name,
                "source_room_name": name,
                "bed_model": normalize_text(raw.get("bed_model")) or None,
                "bed_model_id": normalize_text(raw.get("bed_model_id")) or None,
                "max_minutes": parse_number(raw.get("max_minutes")),
                "startup_minutes": parse_number(raw.get("startup_minutes")),
                "cooldown_minutes": parse_number(raw.get("cooldown_minutes")),
                "current_price_per_min": parse_number(raw.get("current_price_per_min")),
                "status": normalize_text(raw.get("status")) or None,
                "status_code": normalize_text(raw.get("status_code")) or None,
                "lamp_status": normalize_text(raw.get("lamp_status")) or None,
                "raw": {key: value for key, value in raw.items() if key != "name_token"},
            }
        )
    return beds


def set_date_range(page, start: date, end: date) -> None:
    iso_start, iso_end = start.isoformat(), end.isoformat()
    no_start, no_end = start.strftime("%d.%m.%Y"), end.strftime("%d.%m.%Y")
    if page.locator("#member-dates button").count() > 0:
        page.locator("#member-dates button").first.click(timeout=5000)
        page.wait_for_timeout(250)
        custom_range = page.locator(".ranges li").filter(has_text=re.compile("^Valgfri$", re.I))
        if custom_range.count() > 0:
            custom_range.first.click(timeout=5000)
            page.wait_for_timeout(250)
        page.locator('input[name="daterangepicker_start"]').fill(iso_start, timeout=5000)
        page.locator('input[name="daterangepicker_end"]').fill(iso_end, timeout=5000)
        page.locator(".applyBtn").first.click(timeout=5000)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except PwTimeoutError:
            pass
        page.wait_for_timeout(1000)
        return

    inputs = page.locator("input")
    count = inputs.count()
    date_like_indexes: list[int] = []
    for index in range(count):
        field = inputs.nth(index)
        try:
            attrs = " ".join(
                normalize_key(field.get_attribute(attr) or "")
                for attr in ["id", "name", "placeholder", "aria-label", "class", "type"]
            )
            if "date" in attrs or "dato" in attrs or "start" in attrs or "from" in attrs or "fra" in attrs or "end" in attrs or "slutt" in attrs or "til" in attrs:
                date_like_indexes.append(index)
            if any(key in attrs for key in ["start", "from", "fra", "startdate"]):
                field.fill(iso_start if (field.get_attribute("type") or "").lower() == "date" else no_start, timeout=3000)
            elif any(key in attrs for key in ["end", "to", "til", "slutt", "enddate"]):
                field.fill(iso_end if (field.get_attribute("type") or "").lower() == "date" else no_end, timeout=3000)
        except Exception:
            continue

    if len(date_like_indexes) >= 2:
        first = inputs.nth(date_like_indexes[0])
        second = inputs.nth(date_like_indexes[1])
        try:
            first.fill(iso_start if (first.get_attribute("type") or "").lower() == "date" else no_start, timeout=3000)
            second.fill(iso_end if (second.get_attribute("type") or "").lower() == "date" else no_end, timeout=3000)
        except Exception:
            pass

    for label in ["Vis", "Søk", "Sok", "Filter", "Oppdater", "Search", "Show"]:
        if click_text_if_present(page, label):
            return
    try:
        page.keyboard.press("Enter")
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass


def extract_largest_table(page) -> tuple[list[str], list[dict[str, str]]]:
    tables = page.locator("table")
    table_count = tables.count()
    best: tuple[list[str], list[dict[str, str]]] = ([], [])
    best_score = -1
    for index in range(table_count):
        table = tables.nth(index)
        data = table.evaluate(
            """
            table => {
              const domRows = Array.from(table.querySelectorAll('tr'));
              let headers = Array.from(table.querySelectorAll('thead th')).map(th => (th.innerText || '').trim());
              let rows = domRows.map(tr => {
                const cells = Array.from(tr.children);
                const texts = cells.map(td => (td.innerText || '').trim());
                const firstUserLink = tr.querySelector('a.this-user-info, a[data-user-id], a[data-user]');
                return {
                  texts,
                  sun2_user_id: firstUserLink ? (firstUserLink.getAttribute('data-user-id') || '') : '',
                  sun2_user_token: firstUserLink ? (firstUserLink.getAttribute('data-user') || '') : '',
                  user_title: firstUserLink ? (firstUserLink.getAttribute('data-title') || '') : '',
                  user_href: firstUserLink ? (firstUserLink.getAttribute('href') || '') : '',
                };
              }).filter(row => row.texts.some(Boolean));
              let bodyRows = rows;
              if (!headers.length && rows.length) {
                headers = rows[0].texts;
                bodyRows = rows.slice(1);
              }
              if (!headers.length && bodyRows.length) {
                headers = bodyRows[0].texts.map((_, i) => `Kolonne ${i + 1}`);
              }
              return {headers, rows: bodyRows};
            }
            """
        )
        headers = [normalize_text(header) or f"Kolonne {i + 1}" for i, header in enumerate(data.get("headers") or [])]
        rows = []
        for raw_row in data.get("rows") or []:
            texts = raw_row.get("texts") if isinstance(raw_row, dict) else raw_row
            row = {headers[i] if i < len(headers) else f"Kolonne {i + 1}": normalize_text(value) for i, value in enumerate(texts)}
            if isinstance(raw_row, dict):
                row["__sun2_user_id"] = normalize_text(raw_row.get("sun2_user_id"))
                row["__sun2_user_token"] = normalize_text(raw_row.get("sun2_user_token"))
                row["__user_title"] = normalize_text(raw_row.get("user_title"))
                row["__user_href"] = normalize_text(raw_row.get("user_href"))
            if any(row.values()):
                rows.append(row)
        header_keys = {normalize_key(header) for header in headers}
        score = sum(1 for key in ["navn", "betalingsmiddel", "soletid", "kostnad", "solarium", "tidspunkt"] if key in header_keys)
        if score > best_score or (score == best_score and len(rows) > len(best[1])):
            best_score = score
            best = (headers, rows)
    return best


def extract_paginated_table(page, max_pages: int = 500) -> tuple[list[str], list[dict[str, str]]]:
    all_rows: list[dict[str, str]] = []
    headers: list[str] = []
    seen_ranges: set[tuple[int | None, int | None, int | None]] = set()
    for _ in range(max_pages):
        visible_range = extract_visible_sessions_range(page)
        if visible_range != (None, None, None):
            if visible_range in seen_ranges:
                break
            seen_ranges.add(visible_range)
        headers, rows = extract_largest_table(page)
        for row in rows:
            row = dict(row)
            row["__source_row_number"] = str(len(all_rows) + 1)
            all_rows.append(row)
        _, visible_to, visible_total = visible_range
        if visible_to is not None and visible_total is not None and visible_to >= visible_total:
            break
        pager = page.evaluate(
            """
            () => {
              const active = Array.from(document.querySelectorAll('.pagination li.active a, .pagination li.active span, .pagination a.active, .pagination span.active'))
                .map(e => (e.innerText || '').trim()).find(Boolean);
              const pages = Array.from(document.querySelectorAll('.pagination a, .pagination span')).map(a => (a.innerText || '').trim()).filter(Boolean);
              const numericPages = pages.map(text => parseInt(text, 10)).filter(value => Number.isFinite(value));
              return {active, pages, numericPages};
            }
            """
        )
        active_text = normalize_text((pager or {}).get("active"))
        active_page = int(active_text) if active_text.isdigit() else 1
        numeric_pages = sorted({int(value) for value in ((pager or {}).get("numericPages") or [])})
        next_candidates = [value for value in numeric_pages if value > active_page]
        next_page = str(next_candidates[0] if next_candidates else active_page + 1)
        clicked = page.evaluate(
            """
            (nextPage) => {
              const isDisabled = (element) => {
                const item = element.closest('li');
                return element.classList.contains('disabled') || (item && item.classList.contains('disabled'));
              };
              const links = Array.from(document.querySelectorAll('.pagination a')).filter(a => !isDisabled(a));
              let target = links.find(a => (a.innerText || '').trim() === nextPage);
              if (!target) {
                target = links.find(a => {
                  const text = (a.innerText || '').trim().toLowerCase();
                  const className = String(a.className || '').toLowerCase();
                  const itemClassName = String(a.closest('li')?.className || '').toLowerCase();
                  return text === 'neste' || text === 'next' || className.includes('next') || itemClassName.includes('next');
                });
              }
              if (!target) {
                const active = parseInt(nextPage, 10) - 1;
                target = links
                  .map(a => ({element: a, page: parseInt((a.innerText || '').trim(), 10)}))
                  .filter(item => Number.isFinite(item.page) && item.page > active)
                  .sort((a, b) => a.page - b.page)[0]?.element;
              }
              if (!target) return false;
              target.click();
              return true;
            }
            """,
            next_page,
        )
        if not clicked:
            break
        page.wait_for_timeout(900)
    return headers, all_rows


def extract_expected_sessions_count(page) -> int | None:
    text = normalize_text(page.locator("body").inner_text(timeout=5000))
    patterns = [
        r"Solinger\s+i\s+valgt\s+periode\s*\((\d+)\s*st\)",
        r"Viser\s+solinger\s+\d+\s+til\s+\d+\s+av\s+(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return int(match.group(1))
    return None


def extract_visible_sessions_range(page) -> tuple[int | None, int | None, int | None]:
    text = normalize_text(page.locator("body").inner_text(timeout=5000))
    match = re.search(r"Viser\s+(?:solinger|medlemmer)\s+(\d+)\s+til\s+(\d+)\s+av\s+(\d+)", text, re.I)
    if not match:
        return None, None, None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def save_debug(page, filename: str) -> None:
    ERROR_DIR.mkdir(parents=True, exist_ok=True)
    try:
        (ERROR_DIR / f"{filename}.html").write_text(page.content(), encoding="utf-8")
    except Exception:
        pass
    try:
        page.screenshot(path=str(ERROR_DIR / f"{filename}.png"), full_page=True)
    except Exception:
        pass


def post_to_fibaro10(payload: dict[str, Any], endpoint: str = "/api/sun2/sessions/ingest") -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{FIBARO10_API_BASE_URL}{endpoint}",
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Sun2_session_scraper/1.0",
            "x-access-username": FIBARO10_API_USERNAME,
            "x-access-password": FIBARO10_API_PASSWORD,
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {"status": response.status}


def post_import_status(
    job_name: str,
    *,
    ok: bool,
    message: str,
    records_imported: int | None = None,
    records_total: int | None = None,
    raw: dict[str, Any] | None = None,
) -> None:
    titles = {
        "sun2_sessions_import": "Sun2 enkelttimer",
        "sun2_beds_import": "Sun2 senger",
        "sun2_members_import": "Sun2 medlemmer",
    }
    payload = {
        "job_name": job_name,
        "title": titles.get(job_name, job_name.replace("_", " ").title()),
        "category": "Soling",
        "source": "sun2_session_scraper",
        "ok": ok,
        "records_imported": records_imported,
        "records_total": records_total,
        "message": message,
        "raw": {"collector_id": COLLECTOR_ID, **(raw or {})},
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{FIBARO10_API_BASE_URL}/api/import-status/report",
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Sun2_session_scraper/1.0",
            "x-access-username": FIBARO10_API_USERNAME,
            "x-access-password": FIBARO10_API_PASSWORD,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=12):
            pass
    except Exception:
        pass


def post_members_to_fibaro10(payload: dict[str, Any]) -> dict[str, Any] | None:
    members = payload.get("members") or []
    if not members:
        return None
    batch_size = max(1, MEMBER_POST_BATCH_SIZE)
    responses: list[dict[str, Any]] = []
    for index in range(0, len(members), batch_size):
        batch = members[index : index + batch_size]
        batch_payload = dict(payload)
        batch_payload["members"] = batch
        extra = dict(payload.get("extra") or {})
        extra.update(
            {
                "batch_from": index + 1,
                "batch_to": index + len(batch),
                "batch_total": len(members),
                "batch_size": batch_size,
            }
        )
        batch_payload["extra"] = extra
        responses.append(post_to_fibaro10(batch_payload, "/api/sun2/members/ingest"))
    return {
        "batches": len(responses),
        "members": len(members),
        "responses": responses[-3:],
    }


def scrape_beds_sync() -> dict[str, Any]:
    username = env_required("SUN2_USERNAME")
    password = env_required("SUN2_PASSWORD")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="nb-NO", accept_downloads=True)
        page = context.new_page()
        open_beds_page(page, username, password)
        beds = extract_beds(page)
        response = None
        if POST_TO_FIBARO10 and beds:
            response = post_to_fibaro10(
                {
                    "source": "sun2_session_scraper",
                    "collector_id": COLLECTOR_ID,
                    "timestamp": datetime.utcnow().isoformat(),
                    "ok": True,
                    "message": f"Importerte {len(beds)} SUN2-senger",
                    "beds": beds,
                    "extra": {"settings_url": page.url},
                },
                "/api/sun2/beds/ingest",
            )
        context.close()
        browser.close()
    state["beds_last_sync"] = datetime.utcnow().isoformat()
    state["beds_last_count"] = len(beds)
    save_progress({"last_action": "beds_synced", "beds_last_count": len(beds), "fibaro10_beds_response": response})
    post_import_status(
        "sun2_beds_import",
        ok=True,
        message=f"Synket {len(beds)} senger",
        records_imported=len(beds),
        records_total=len(beds),
        raw={"posted": bool(response), "response": response},
    )
    return {"ok": True, "beds": len(beds), "posted": bool(response), "fibaro10_response": response}


def scrape_members_sync() -> dict[str, Any]:
    username = env_required("SUN2_USERNAME")
    password = env_required("SUN2_PASSWORD")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = "Sun2_members.json"
    out_path = OUT_DIR / filename
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="nb-NO", accept_downloads=True)
        page = context.new_page()
        open_members_page(page, username, password)
        headers, table_rows = extract_paginated_table(page, max_pages=1000)
        profile_cache: dict[str, dict[str, str]] = {}
        if FETCH_MEMBER_PROFILES:
            profile_page = context.new_page()
            for row in table_rows[: max(0, MEMBER_PROFILE_LIMIT)]:
                href = absolute_url(row.get("__user_href"))
                if not href:
                    continue
                try:
                    profile_page.goto(href, wait_until="domcontentloaded", timeout=15000)
                    login_if_needed(profile_page, username, password)
                    try:
                        profile_page.wait_for_load_state("networkidle", timeout=8000)
                    except PwTimeoutError:
                        pass
                    profile_cache[href] = profile_pairs_from_page(profile_page)
                    profile_page.wait_for_timeout(150)
                except Exception:
                    profile_cache[href] = {}
            profile_page.close()
        members = []
        seen: set[str] = set()
        for row in table_rows:
            href = absolute_url(row.get("__user_href"))
            item = normalize_member_row(row, profile_cache.get(href))
            if not item or item["sun2_user_id"] in seen:
                continue
            item["source_file"] = filename
            seen.add(item["sun2_user_id"])
            members.append(item)
        payload = {
            "source": "sun2_session_scraper",
            "collector_id": COLLECTOR_ID,
            "timestamp": datetime.utcnow().isoformat(),
            "ok": True,
            "message": f"Skrapet {len(members)} SUN2-medlemmer",
            "members": members,
            "extra": {
                "headers": headers,
                "raw_rows": len(table_rows),
                "members_url": page.url,
                "profile_fetch_enabled": FETCH_MEMBER_PROFILES,
                "profile_limit": MEMBER_PROFILE_LIMIT,
            },
        }
        tmp_path = out_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        tmp_path.replace(out_path)
        response = None
        if POST_TO_FIBARO10 and members:
            response = post_members_to_fibaro10(payload)
        context.close()
        browser.close()

    named_count = sum(1 for item in members if item.get("name"))
    state["members_last_sync"] = datetime.utcnow().isoformat()
    state["members_last_count"] = len(members)
    state["members_last_named_count"] = named_count
    save_progress(
        {
            "last_action": "members_synced",
            "members_last_count": len(members),
            "members_last_named_count": named_count,
            "fibaro10_members_response": response,
        }
    )
    post_import_status(
        "sun2_members_import",
        ok=True,
        message=f"Synket {len(members)} medlemmer, {named_count} med navn",
        records_imported=len(members),
        records_total=len(members),
        raw={"posted": bool(response), "named_count": named_count, "response": response},
    )
    return {"ok": True, "members": len(members), "named": named_count, "posted": bool(response), "fibaro10_response": response}


def scrape_month_sync(start: date, end: date) -> dict[str, Any]:
    username = env_required("SUN2_USERNAME")
    password = env_required("SUN2_PASSWORD")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ERROR_DIR.mkdir(parents=True, exist_ok=True)
    filename = filename_for(start)
    out_path = OUT_DIR / filename
    state.update({"last_period": f"{start.isoformat()} - {end.isoformat()}", "current_file": filename, "rows_last_file": 0})

    period_is_still_open = end >= local_today()
    if SKIP_EXISTING and out_path.exists() and not period_is_still_open:
        state["skipped_files"] += 1
        state["last_success_period"] = state["last_period"]
        save_progress({"last_action": "skipped_existing"})
        post_import_status(
            "sun2_sessions_import",
            ok=True,
            message=f"Hoppet over eksisterende fil {filename}",
            records_imported=0,
            records_total=0,
            raw={"source_file": filename, "skipped": True},
        )
        return {"ok": True, "skipped": True, "file": filename, "rows": 0}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="nb-NO", accept_downloads=True)
        page = context.new_page()
        open_sessions_page(page, username, password)
        set_date_range(page, start, end)
        expected_count = extract_expected_sessions_count(page)
        headers, table_rows = extract_paginated_table(page)
        sessions = [item for item in (normalize_session_row(row, start) for row in table_rows) if item]
        if expected_count is not None and len(sessions) != expected_count:
            save_debug(page, f"COUNT_MISMATCH_{start:%Y_%m}")
            raise RuntimeError(f"Antall stemmer ikke for {start.isoformat()} - {end.isoformat()}: fant {len(sessions)} av {expected_count}")
        outside_period = [
            item
            for item in sessions
            if not (start <= date.fromisoformat(item["stat_date"]) <= end)
        ]
        if outside_period:
            save_debug(page, f"DATE_MISMATCH_{start:%Y_%m}")
            sample = outside_period[0].get("started_at") or outside_period[0].get("stat_date")
            raise RuntimeError(f"Dato-filter feilet for {start.isoformat()} - {end.isoformat()}, eksempelrad: {sample}")
        if not sessions:
            save_debug(page, f"NO_ROWS_{start:%Y_%m}")
        payload = {
            "source": "sun2_session_scraper",
            "collector_id": COLLECTOR_ID,
            "timestamp": datetime.utcnow().isoformat(),
            "ok": True,
            "source_file": filename,
            "message": f"Skrapet {start.isoformat()} til {end.isoformat()}",
            "rows": sessions,
            "extra": {
                "period_start": start.isoformat(),
                "period_end": end.isoformat(),
                "headers": headers,
                "raw_rows": len(table_rows),
                "list_url": page.url,
            },
        }
        tmp_path = out_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        tmp_path.replace(out_path)
        response = None
        if POST_TO_FIBARO10 and sessions:
            response = post_to_fibaro10(payload)
            state["posted_files"] += 1
        context.close()
        browser.close()

    state["created_files"] += 1
    state["rows_last_file"] = len(sessions)
    state["last_success_period"] = state["last_period"]
    state["last_success_at"] = datetime.utcnow().isoformat()
    state["last_error"] = None
    save_progress({"last_action": "created", "fibaro10_response": response})
    post_import_status(
        "sun2_sessions_import",
        ok=True,
        message=f"Skrapet {filename} med {len(sessions)} enkelttimer",
        records_imported=len(sessions),
        records_total=expected_count if expected_count is not None else len(sessions),
        raw={"source_file": filename, "posted": bool(response), "response": response},
    )
    return {"ok": True, "file": filename, "rows": len(sessions), "posted": bool(response), "fibaro10_response": response}


def start_date_from_progress(config_start: date) -> date:
    progress = load_progress()
    last_period = progress.get("last_success_period") or ""
    match = re.search(r"(\d{4}-\d{2}-\d{2})\s*-\s*(\d{4}-\d{2}-\d{2})", last_period)
    if not match:
        return config_start
    try:
        next_day = date.fromisoformat(match.group(2)) + timedelta(days=1)
        return max(config_start, next_day)
    except ValueError:
        return config_start


def run_range_sync() -> None:
    global stop_requested
    try:
        configured_start = parse_date(env_value("START_DATE"), local_today().replace(day=1))
        end = parse_date(env_value("END_DATE"), local_today())
        start = start_date_from_progress(configured_start)
        state.update(
            {
                "running": True,
                "stop_requested": False,
                "last_error": None,
                "range": {"start": start.isoformat(), "end": end.isoformat(), "configured_start": configured_start.isoformat()},
            }
        )
        save_progress({})
        try:
            scrape_beds_sync()
        except Exception as exc:
            state["last_error"] = f"Seng-sync feilet: {exc}"
            save_progress({"last_action": "beds_failed"})
            post_import_status("sun2_beds_import", ok=False, message=state["last_error"])
        for period_start, period_end in iter_month_ranges(start, end):
            if stop_requested:
                state["stop_requested"] = True
                break
            try:
                scrape_month_sync(period_start, period_end)
            except Exception as exc:
                state["failed"] += 1
                state["last_error"] = f"{period_start:%Y-%m}: {exc}"
                save_progress({"last_action": "failed"})
                post_import_status(
                    "sun2_sessions_import",
                    ok=False,
                    message=state["last_error"],
                    raw={"period_start": period_start.isoformat(), "period_end": period_end.isoformat()},
                )
            if PAUSE_SECONDS > 0:
                time.sleep(PAUSE_SECONDS)
    except Exception as exc:
        state["last_error"] = str(exc)
        save_progress({"last_action": "fatal_error"})
        post_import_status("sun2_sessions_import", ok=False, message=f"Fatal scraper-feil: {exc}")
    finally:
        state["running"] = False
        state["current_file"] = None
        save_progress({"last_action": "stopped" if stop_requested else "finished"})
        stop_requested = False


async def ensure_task_started() -> bool:
    global task, stop_requested
    if task and not task.done():
        return False
    stop_requested = False
    task = asyncio.create_task(asyncio.to_thread(run_range_sync))
    return True


async def run_scheduled_job(job_key: str, job_name: str, runner) -> None:
    if schedule_lock.locked():
        return
    async with schedule_lock:
        now = local_now()
        mark_scheduled_attempt(job_key, now)
        save_progress({"last_action": f"scheduled_{job_key}_started"})
        try:
            result = await asyncio.to_thread(runner)
            state["last_error"] = None
            save_progress({"last_action": f"scheduled_{job_key}_finished", "scheduled_result": result})
        except Exception as exc:
            state["last_error"] = f"Nattlig {job_key} feilet: {exc}"
            save_progress({"last_action": f"scheduled_{job_key}_failed"})
            post_import_status(job_name, ok=False, message=state["last_error"], raw={"job_key": job_key})


def current_month_runner():
    today = local_today()
    return scrape_month_sync(today.replace(day=1), today)


async def nightly_scheduler_loop() -> None:
    while True:
        try:
            now = local_now()
            state["scheduler_last_check"] = now.isoformat()
            if SCHEDULE_ENABLED:
                if schedule_due("sessions", SCHEDULE_SESSIONS_TIME, now):
                    if task and not task.done():
                        state["scheduler_last_action"] = "sessions venter paa range-jobb"
                    else:
                        await run_scheduled_job("sessions", "sun2_sessions_import", current_month_runner)
                if schedule_due("beds", SCHEDULE_BEDS_TIME, now):
                    await run_scheduled_job("beds", "sun2_beds_import", scrape_beds_sync)
                if schedule_due("members", SCHEDULE_MEMBERS_TIME, now):
                    await run_scheduled_job("members", "sun2_members_import", scrape_members_sync)
            save_progress({"last_action": "scheduler_check"})
        except Exception as exc:
            state["last_error"] = f"Scheduler feilet: {exc}"
            save_progress({"last_action": "scheduler_failed"})
        await asyncio.sleep(max(30, SCHEDULE_POLL_SECONDS))


@app.on_event("startup")
async def startup() -> None:
    global scheduler_task
    progress = load_progress()
    if progress:
        state.update({key: value for key, value in progress.items() if key in state})
    if AUTO_START:
        await ensure_task_started()
    if SCHEDULE_ENABLED and (scheduler_task is None or scheduler_task.done()):
        scheduler_task = asyncio.create_task(nightly_scheduler_loop())


@app.get("/", response_class=HTMLResponse)
async def index():
    status_class = "ok" if not state.get("last_error") else "bad"
    html = f"""
<!doctype html>
<html lang="no">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sun2 enkeltimer</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#eef2f6;color:#17202a}}
main{{max-width:980px;margin:0 auto;padding:1rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:.7rem}}
.card{{background:white;border:1px solid #d8dee4;border-radius:10px;padding:1rem;margin:.75rem 0;box-shadow:0 2px 10px rgba(0,0,0,.06)}}
.metric{{background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px;padding:.75rem}}
.metric span{{display:block;color:#667085;font-size:.78rem}}
.metric strong{{display:block;margin-top:.2rem;font-size:1.05rem}}
.ok{{color:#16803c;font-weight:750}}.bad{{color:#b42318;font-weight:750}}
button{{border:0;border-radius:8px;background:#4b86c2;color:white;padding:.65rem .9rem;font-weight:750;margin-right:.4rem}}
.stop{{background:#b42318}} pre{{white-space:pre-wrap;background:#0f172a;color:#e5e7eb;border-radius:8px;padding:.75rem;overflow:auto}}
input{{border:1px solid #ccd6e0;border-radius:8px;padding:.55rem .65rem;margin-right:.35rem}}
</style></head>
<body><main>
<h1>Sun2 enkeltimer</h1>
<section class="card grid">
<div class="metric"><span>Status</span><strong class="{status_class}">{'Kjører' if state.get('running') else ('Feil' if state.get('last_error') else 'Klar')}</strong></div>
<div class="metric"><span>Periode</span><strong>{state.get('last_period') or '-'}</strong></div>
<div class="metric"><span>Siste OK</span><strong>{state.get('last_success_period') or '-'}</strong></div>
<div class="metric"><span>Filer</span><strong>{state.get('created_files', 0)}</strong></div>
<div class="metric"><span>Postet</span><strong>{state.get('posted_files', 0)}</strong></div>
<div class="metric"><span>Siste rader</span><strong>{state.get('rows_last_file', 0)}</strong></div>
<div class="metric"><span>Medlemmer</span><strong>{state.get('members_last_count', 0)}</strong></div>
<div class="metric"><span>Navn funnet</span><strong>{state.get('members_last_named_count', 0)}</strong></div>
<div class="metric"><span>Nattjobb</span><strong>{'PÃ¥' if SCHEDULE_ENABLED else 'Av'}</strong></div>
<div class="metric"><span>Tider</span><strong>{SCHEDULE_SESSIONS_TIME} / {SCHEDULE_BEDS_TIME} / {SCHEDULE_MEMBERS_TIME}</strong></div>
<div class="metric"><span>Siste sjekk</span><strong>{state.get('scheduler_last_check') or '-'}</strong></div>
<div class="metric"><span>Siste nattjobb</span><strong>{state.get('scheduler_last_action') or '-'}</strong></div>
</section>
<section class="card">
<form method="post" action="/start" style="display:inline"><button type="submit">Start range</button></form>
<form method="post" action="/stop" style="display:inline"><button class="stop" type="submit">Stopp</button></form>
<form method="post" action="/sync-current-month" style="display:inline"><button type="submit">Denne måneden</button></form>
<form method="post" action="/sync-beds" style="display:inline"><button type="submit">Synk senger</button></form>
<form method="post" action="/sync-members" style="display:inline"><button type="submit">Synk medlemmer</button></form>
</section>
<section class="card">
<form method="post" action="/sync-month">
<input name="year" type="number" min="2017" max="2100" value="{local_today().year}">
<input name="month" type="number" min="1" max="12" value="{local_today().month}">
<button type="submit">Kjør valgt måned</button>
</form>
</section>
<section class="card"><pre>{json.dumps(state, ensure_ascii=False, indent=2)}</pre></section>
</main></body></html>
"""
    return HTMLResponse(html)


@app.post("/start")
async def start():
    await ensure_task_started()
    return RedirectResponse("/", status_code=303)


@app.post("/stop")
async def stop():
    global stop_requested
    stop_requested = True
    state["stop_requested"] = True
    return RedirectResponse("/", status_code=303)


@app.post("/sync-current-month")
async def sync_current_month():
    today = local_today()
    start = today.replace(day=1)
    end = today
    try:
        result = await asyncio.to_thread(scrape_month_sync, start, end)
        return JSONResponse({"status": "ok", "result": result, "state": state})
    except Exception as exc:
        state["last_error"] = f"Denne måneden feilet: {exc}"
        save_progress({"last_action": "manual_month_failed"})
        post_import_status("sun2_sessions_import", ok=False, message=state["last_error"])
        return JSONResponse({"status": "error", "error": str(exc), "state": state}, status_code=500)


@app.post("/sync-beds")
async def sync_beds():
    try:
        result = await asyncio.to_thread(scrape_beds_sync)
        return JSONResponse({"status": "ok", "result": result, "state": state})
    except Exception as exc:
        state["last_error"] = f"Manuell seng-sync feilet: {exc}"
        save_progress({"last_action": "beds_failed"})
        post_import_status("sun2_beds_import", ok=False, message=state["last_error"])
        return JSONResponse({"status": "error", "error": str(exc), "state": state}, status_code=500)


@app.post("/sync-members")
async def sync_members():
    try:
        result = await asyncio.to_thread(scrape_members_sync)
        return JSONResponse({"status": "ok", "result": result, "state": state})
    except Exception as exc:
        state["last_error"] = f"Manuell medlems-sync feilet: {exc}"
        save_progress({"last_action": "members_failed"})
        post_import_status("sun2_members_import", ok=False, message=state["last_error"])
        return JSONResponse({"status": "error", "error": str(exc), "state": state}, status_code=500)


@app.post("/sync-month")
async def sync_month(request: Request, year: int | None = Query(None), month: int | None = Query(None)):
    if year is None or month is None:
        body = (await request.body()).decode("utf-8")
        from urllib.parse import parse_qs

        form = parse_qs(body)
        year = int((form.get("year") or [local_today().year])[0])
        month = int((form.get("month") or [local_today().month])[0])
    start = date(year, month, 1)
    end = min(month_end(start), local_today())
    try:
        result = await asyncio.to_thread(scrape_month_sync, start, end)
        return JSONResponse({"status": "ok", "result": result, "state": state})
    except Exception as exc:
        state["last_error"] = f"Manuell måned {year}-{month:02d} feilet: {exc}"
        save_progress({"last_action": "manual_month_failed"})
        post_import_status(
            "sun2_sessions_import",
            ok=False,
            message=state["last_error"],
            raw={"year": year, "month": month},
        )
        return JSONResponse({"status": "error", "error": str(exc), "state": state}, status_code=500)


@app.get("/json")
async def json_status():
    return JSONResponse(state)
