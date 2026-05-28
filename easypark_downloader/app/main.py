import asyncio
import email
import imaplib
import json
import os
import re
import shutil
from datetime import date, datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.message import Message
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from playwright.async_api import async_playwright

load_dotenv()

DATA_DIR = Path(os.getenv("EASYPARK_DATA_DIR", "/data"))
PROFILE_DIR = DATA_DIR / "browser-profile"
DOWNLOAD_DIR = DATA_DIR / "downloads"
ARTIFACT_DIR = DATA_DIR / "artifacts"
STATE_PATH = DATA_DIR / "state.json"
AUTH_STATE_PATH = DATA_DIR / "auth-state.json"

REPORT_URL = os.getenv("EASYPARK_REPORT_URL", "https://dashboard.easypark.net/search-parkings/1")
RUN_INTERVAL_MINUTES = int(os.getenv("EASYPARK_RUN_INTERVAL_MINUTES", "2"))
RUN_AT = os.getenv("EASYPARK_RUN_AT", "").strip()
RUN_TIMES = os.getenv("EASYPARK_RUN_TIMES", "").strip()
RUN_EVERY_HOUR = os.getenv("EASYPARK_RUN_EVERY_HOUR", "false").strip().lower() in {"1", "true", "yes", "ja"}
RUN_MINUTE = max(0, min(59, int(os.getenv("EASYPARK_RUN_MINUTE", "0"))))
RUN_ON_START = os.getenv("EASYPARK_RUN_ON_START", "false").strip().lower() in {"1", "true", "yes", "ja"}
SCHEDULE_MODE = os.getenv("EASYPARK_SCHEDULE_MODE", "recent").strip().lower()
RECENT_DAYS = max(1, int(os.getenv("EASYPARK_RECENT_DAYS", "2")))
HEADLESS = os.getenv("EASYPARK_HEADLESS", "true").strip().lower() not in {"0", "false", "no", "nei"}
CODE_COOLDOWN_MINUTES = int(os.getenv("EASYPARK_CODE_COOLDOWN_MINUTES", "5"))
FORCE_LOGIN_TIMES = os.getenv("EASYPARK_FORCE_LOGIN_TIMES", "03:00").strip()
EDGE_EXECUTABLE_PATH = os.getenv("EASYPARK_EDGE_EXECUTABLE_PATH", "/usr/bin/microsoft-edge")
LOCAL_TZ = ZoneInfo("Europe/Oslo")

FIBARO10_BASE_URL = os.getenv("FIBARO10_BASE_URL", "http://192.168.20.218:8110").rstrip("/")
FIBARO10_USERNAME = os.getenv("FIBARO10_USERNAME", "")
FIBARO10_PASSWORD = os.getenv("FIBARO10_PASSWORD", "")

IMAP_HOST = "imap.gmail.com"
FROM_ADDRESS = "no-reply@easypark.net"
SUBJECT_TEXT = "EasyPark - Verification Code"
CODE_RE = re.compile(r"verification code is:\s*(\d{4,8})", re.IGNORECASE)

app = FastAPI(title="EasyPark downloader")
lock = asyncio.Lock()
worker_task: asyncio.Task | None = None
state: dict[str, Any] = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "running": False,
    "last_success_at": None,
    "last_error": None,
    "last_file": None,
    "last_import": None,
    "last_period": None,
    "last_action": "init",
}


def env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def fibaro10_datetime_iso() -> str:
    return datetime.now(LOCAL_TZ).replace(tzinfo=None, microsecond=0).isoformat()


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def easypark_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def period_label(from_day: date | None, to_day: date | None) -> str:
    if not from_day and not to_day:
        return "standard"
    return f"{from_day.isoformat() if from_day else '-'} - {to_day.isoformat() if to_day else '-'}"


def validate_period(from_day: date | None, to_day: date | None) -> None:
    if bool(from_day) != bool(to_day):
        raise RuntimeError("EasyPark-perioden må ha både fra- og til-dato.")
    if not from_day or not to_day:
        return
    if from_day > to_day:
        raise RuntimeError("Fra-dato kan ikke være etter til-dato.")
    if to_day - from_day > timedelta(days=366):
        raise RuntimeError("EasyPark tillater maks ett år per eksport.")


def scheduled_period() -> tuple[date | None, date | None]:
    if SCHEDULE_MODE not in {"recent", "rolling"}:
        return None, None
    today = datetime.now(LOCAL_TZ).date()
    return today - timedelta(days=RECENT_DAYS - 1), today


def set_state(**values: Any) -> None:
    state.update(values)


def read_auth_state() -> dict[str, Any]:
    if not AUTH_STATE_PATH.exists():
        return {}
    try:
        return json.loads(AUTH_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_auth_state(**values: Any) -> None:
    current = read_auth_state()
    current.update(values)
    AUTH_STATE_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")


def reset_browser_profile(reason: str) -> None:
    if PROFILE_DIR.exists():
        shutil.rmtree(PROFILE_DIR)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    write_auth_state(
        last_reset_at=utcnow_iso(),
        last_reset_reason=reason,
        last_logout_at=utcnow_iso(),
        last_login_at=None,
    )


def mark_login_completed() -> None:
    write_auth_state(last_login_at=utcnow_iso())


def parse_run_times(value: str) -> list[tuple[int, int]]:
    times: list[tuple[int, int]] = []
    for part in re.split(r"[,;\s]+", value.strip()):
        if not part:
            continue
        match = re.match(r"^(\d{1,2})(?::(\d{2}))?$", part)
        if not match:
            continue
        hour = max(0, min(23, int(match.group(1))))
        minute = max(0, min(59, int(match.group(2) or "0")))
        item = (hour, minute)
        if item not in times:
            times.append(item)
    return sorted(times)


def decoded_header(raw: str | None) -> str:
    return str(make_header(decode_header(raw))) if raw else ""


def message_text(message: Message) -> str:
    parts: list[str] = []
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_disposition() == "attachment":
                continue
            if part.get_content_type() not in {"text/plain", "text/html"}:
                continue
            payload = part.get_payload(decode=True)
            if payload:
                parts.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
    else:
        payload = message.get_payload(decode=True)
        if payload:
            parts.append(payload.decode(message.get_content_charset() or "utf-8", errors="replace"))
    return "\n".join(parts)


def fetch_latest_code(after: datetime | None = None, max_age_minutes: int = 20) -> str:
    gmail_email = env_required("EASYPARK_GMAIL_EMAIL")
    app_password = env_required("EASYPARK_GMAIL_APP_PASSWORD").replace(" ", "")
    since = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")

    with imaplib.IMAP4_SSL(IMAP_HOST) as mailbox:
        mailbox.login(gmail_email, app_password)
        mailbox.select("INBOX", readonly=True)
        status, data = mailbox.search(None, f'(FROM "{FROM_ADDRESS}" SINCE "{since}")')
        if status != "OK" or not data or not data[0]:
            raise RuntimeError("Fant ingen EasyPark-verifikasjonsmail siste døgn.")

        candidates: list[tuple[datetime, str]] = []
        for message_id in data[0].split():
            status, raw_data = mailbox.fetch(message_id, "(RFC822)")
            if status != "OK" or not raw_data:
                continue
            raw_message = raw_data[0][1]
            message = email.message_from_bytes(raw_message)
            if SUBJECT_TEXT.lower() not in decoded_header(message.get("Subject")).lower():
                continue
            message_date = email.utils.parsedate_to_datetime(message.get("Date"))
            if message_date:
                comparable_now = datetime.now(message_date.tzinfo) if message_date.tzinfo else datetime.now()
                if comparable_now - message_date > timedelta(minutes=max_age_minutes):
                    continue
                if after:
                    comparable_after = after
                    if comparable_after.tzinfo is None and message_date.tzinfo:
                        comparable_after = comparable_after.replace(tzinfo=message_date.tzinfo)
                    elif comparable_after.tzinfo and message_date.tzinfo:
                        comparable_after = comparable_after.astimezone(message_date.tzinfo)
                    if message_date < comparable_after:
                        continue
            match = CODE_RE.search(message_text(message))
            if match:
                candidates.append((message_date or datetime.min, match.group(1)))

    if not candidates:
        raise RuntimeError("Fant ingen fersk EasyPark-kode i Gmail.")
    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]


async def page_text(page) -> str:
    return await page.evaluate("document.body.innerText || ''")


async def click_visible(locator) -> bool:
    count = await locator.count()
    for index in range(count):
        item = locator.nth(index)
        if await item.is_visible(timeout=1000):
            await item.click()
            return True
    return False


async def click_button_by_name(page, pattern: re.Pattern[str]) -> bool:
    button = page.get_by_role("button", name=pattern).first
    if await button.is_visible(timeout=1500):
        await button.click()
        return True
    return False


async def fill_code(page, code: str) -> bool:
    locators = [
        page.get_by_placeholder(re.compile("enter code", re.I)),
        page.get_by_label(re.compile("enter code|verification code|code|kode", re.I)),
        page.locator('input[autocomplete="one-time-code"]'),
        page.locator('input[name*="code" i], input[id*="code" i]'),
        page.locator('input[inputmode="numeric"], input[type="tel"]'),
    ]
    for locator in locators:
        for index in range(await locator.count()):
            field = locator.nth(index)
            if await field.is_visible(timeout=800):
                await field.fill(code)
                return True

    inputs = page.locator("input")
    visible = []
    for index in range(await inputs.count()):
        item = inputs.nth(index)
        if await item.is_visible(timeout=500):
            visible.append(item)
    if len(visible) == 1:
        await visible[0].fill(code)
        return True
    if len(visible) >= len(code):
        for index, digit in enumerate(code):
            await visible[index].fill(digit)
        return True
    return False


async def looks_logged_in(page) -> bool:
    body = await page_text(page)
    return not re.search(r"sign in|username|password", body, re.I) and bool(
        re.search(r"export to file|parking areas|search parkings|metrics", body, re.I)
    )


async def save_debug(page, name: str) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / f"{name}.txt").write_text((await page_text(page))[:5000], encoding="utf-8")
    await page.screenshot(path=str(ARTIFACT_DIR / f"{name}.png"), full_page=True)


async def ensure_logged_in(page) -> bool:
    await page.goto(REPORT_URL, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(5000)
    if await looks_logged_in(page):
        if not parse_iso_datetime(read_auth_state().get("last_login_at")):
            mark_login_completed()
        return False

    performed_login = False
    body = await page_text(page)
    if re.search(r"sign in|username|password", body, re.I):
        # EasyPark can leave the login form in a stale state after logout.
        # Reload before entering credentials so the MFA/email-code flow is initialized cleanly.
        await page.reload(wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)
        await page.get_by_placeholder("Enter your username").fill(env_required("EASYPARK_USERNAME"))
        await page.get_by_placeholder("Enter your password").fill(env_required("EASYPARK_PASSWORD"))
        await page.get_by_role("button", name=re.compile("^Sign in$", re.I)).click()
        performed_login = True
        await page.wait_for_timeout(6000)

    body = await page_text(page)
    requested_at: datetime | None = None
    if re.search(r"send code via email", body, re.I):
        mfa_errors: list[str] = []

        async def capture_mfa_response(response) -> None:
            if "/api/login-flow/authentication/mfa" not in response.url:
                return
            try:
                text = await response.text()
            except Exception:
                text = ""
            if "RECAPTCHA_FAILED" in text:
                mfa_errors.append("recaptcha")

        page.on("response", lambda response: asyncio.create_task(capture_mfa_response(response)))
        await page.get_by_role("button", name=re.compile("^Send code via email$", re.I)).click()
        requested_at = datetime.now(timezone.utc)
        set_state(last_action="requested_email_code")
        await page.wait_for_timeout(max(8000, CODE_COOLDOWN_MINUTES * 1000))
        if mfa_errors:
            await save_debug(page, "easypark-recaptcha-email-code")
            raise RuntimeError("EasyPark stopper automatisk bestilling av e-postkode med reCAPTCHA.")

    body = await page_text(page)
    if re.search(r"please check your login or password", body, re.I):
        await save_debug(page, "easypark-login-rejected")
        if requested_at:
            raise RuntimeError("EasyPark stopper automatisk bestilling av e-postkode, selv om brukernavn/passord ble akseptert.")
        raise RuntimeError("EasyPark avviser brukernavn/passord eller blokkerer automatisk login.")

    if re.search(r"recaptcha|security check", body, re.I):
        await save_debug(page, "easypark-security-check")
        raise RuntimeError("EasyPark krever manuell sikkerhetskontroll.")

    if re.search(r"enter code|verification code|code|kode", body, re.I):
        code = fetch_latest_code(after=requested_at)
        if not await fill_code(page, code):
            await save_debug(page, "easypark-code-field-missing")
            raise RuntimeError("Fant ikke felt for EasyPark-verifikasjonskode.")
        await click_button_by_name(page, re.compile("verify|bekreft|continue|fortsett|submit|sign in|logg inn", re.I))
        await page.keyboard.press("Enter")
        performed_login = True
        await page.wait_for_timeout(7000)

    if not await looks_logged_in(page):
        await save_debug(page, "easypark-login-failed")
        raise RuntimeError("EasyPark-login fullførte ikke.")

    await page.goto(REPORT_URL, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(5000)
    if not await looks_logged_in(page):
        await save_debug(page, "easypark-report-not-ready")
        raise RuntimeError("EasyPark-rapporten ble ikke tilgjengelig etter login.")
    if performed_login:
        mark_login_completed()
    return performed_login


async def logout_easypark(page) -> bool:
    try:
        await page.goto(REPORT_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2000)
        if not await looks_logged_in(page):
            return False
        patterns = [
            re.compile(r"sign out|log out|logout", re.I),
            re.compile(r"logg ut", re.I),
        ]
        for pattern in patterns:
            if await click_visible(page.get_by_role("button", name=pattern)):
                await page.wait_for_timeout(2000)
                return True
            if await click_visible(page.get_by_role("link", name=pattern)):
                await page.wait_for_timeout(2000)
                return True
        menu_candidates = [
            page.locator('[aria-label*="user" i], [aria-label*="account" i], [aria-label*="profile" i]'),
            page.locator(".user-menu, .profile-menu, .account-menu, .dropdown-toggle"),
        ]
        for menu in menu_candidates:
            if await click_visible(menu):
                await page.wait_for_timeout(1000)
                for pattern in patterns:
                    if await click_visible(page.get_by_role("button", name=pattern)):
                        await page.wait_for_timeout(2000)
                        return True
                    if await click_visible(page.get_by_role("link", name=pattern)):
                        await page.wait_for_timeout(2000)
                        return True
    except Exception:
        return False
    return False


async def try_logout_existing_session(playwright) -> bool:
    if not PROFILE_DIR.exists():
        return False
    launch_options: dict[str, Any] = {}
    if EDGE_EXECUTABLE_PATH and Path(EDGE_EXECUTABLE_PATH).exists():
        launch_options["executable_path"] = EDGE_EXECUTABLE_PATH
    context = await playwright.chromium.launch_persistent_context(
        str(PROFILE_DIR),
        headless=HEADLESS,
        accept_downloads=False,
        viewport={"width": 1365, "height": 900},
        locale="en-US",
        timezone_id="Europe/Oslo",
        **launch_options,
    )
    page = context.pages[0] if context.pages else await context.new_page()
    try:
        return await logout_easypark(page)
    finally:
        try:
            await context.close()
        except Exception:
            pass


async def download_report(page) -> Path:
    body = await page_text(page)
    if not re.search(r"export to file", body, re.I):
        await save_debug(page, "easypark-export-missing")
        raise RuntimeError("Fant ikke 'Export to file' i EasyPark.")

    download_task = asyncio.create_task(page.wait_for_event("download", timeout=60000))
    clicked = await click_visible(page.get_by_role("button", name=re.compile("export to file", re.I)))
    if not clicked:
        download_task.cancel()
        raise RuntimeError("Klarte ikke å trykke på 'Export to file'.")

    try:
        download = await asyncio.wait_for(asyncio.shield(download_task), timeout=2)
    except asyncio.TimeoutError:
        option_clicked = (
            await click_visible(page.get_by_role("link", name=re.compile("download csv|csv", re.I)))
            or await click_visible(page.locator("a.sp-download-csv"))
            or await click_visible(page.locator(".dropdown-menu a, .dropdown-menu button"))
        )
        if not option_clicked:
            download_task.cancel()
            await save_debug(page, "easypark-export-stuck")
            raise RuntimeError("Eksportmenyen åpnet, men jeg fant ikke CSV-valget.")
        download = await download_task

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    extension = Path(download.suggested_filename).suffix or ".csv"
    target = DOWNLOAD_DIR / f"easypark-parkings-{stamp()}{extension}"
    await download.save_as(str(target))
    return target


MONTH_NAMES = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


async def datepicker_month_year(page) -> tuple[int, int]:
    text = (await page.locator(".react-datepicker__current-month").first.inner_text(timeout=5000)).strip()
    parts = text.split()
    if len(parts) != 2 or parts[0] not in MONTH_NAMES:
        raise RuntimeError(f"Ukjent EasyPark-kalendermåned: {text}")
    return MONTH_NAMES[parts[0]], int(parts[1])


async def pick_date(page, field_index: int, target_day: date) -> None:
    date_fields = page.locator("input.form-control")
    if await date_fields.count() <= field_index:
        await save_debug(page, "easypark-date-fields-missing")
        raise RuntimeError("Fant ikke EasyPark-feltene for fra/til-dato.")

    await date_fields.nth(field_index).click()
    await page.locator(".react-datepicker").wait_for(state="visible", timeout=5000)

    for _ in range(24):
        current_month, current_year = await datepicker_month_year(page)
        delta = (target_day.year - current_year) * 12 + (target_day.month - current_month)
        if delta == 0:
            break
        selector = ".react-datepicker__navigation--next" if delta > 0 else ".react-datepicker__navigation--previous"
        await page.locator(selector).first.click()
        await page.wait_for_timeout(250)
    else:
        await save_debug(page, "easypark-datepicker-navigation-failed")
        raise RuntimeError(f"Klarte ikke å navigere EasyPark-kalenderen til {target_day.isoformat()}.")

    day_selector = f".react-datepicker__day--{target_day.day:03d}:not(.react-datepicker__day--outside-month)"
    day = page.locator(day_selector).first
    if not await day.is_visible(timeout=3000):
        await save_debug(page, "easypark-datepicker-day-missing")
        raise RuntimeError(f"Fant ikke dato {target_day.isoformat()} i EasyPark-kalenderen.")
    await day.click()
    await page.wait_for_timeout(500)


async def set_date_range(page, from_day: date | None, to_day: date | None) -> None:
    validate_period(from_day, to_day)
    if not from_day or not to_day:
        return

    date_fields = page.locator("input.form-control")
    if await date_fields.count() < 5:
        await save_debug(page, "easypark-date-fields-missing")
        raise RuntimeError("Fant ikke EasyPark-feltene for fra/til-dato.")

    await pick_date(page, 3, from_day)
    await pick_date(page, 4, to_day)
    await page.wait_for_timeout(1000)

    actual_values = await date_fields.evaluate_all("(fields) => fields.slice(3, 5).map((field) => field.value)")
    if actual_values[:2] != [easypark_date(from_day), easypark_date(to_day)]:
        await save_debug(page, "easypark-date-values-not-set")
        raise RuntimeError(f"EasyPark beholdt feil datoer: {actual_values[:2]}")

    clicked = await click_visible(page.get_by_role("button", name=re.compile("^Search$", re.I)))
    if not clicked:
        await save_debug(page, "easypark-search-button-missing")
        raise RuntimeError("Fant ikke EasyPark-søkeknappen etter datovalg.")
    await page.wait_for_timeout(8000)

    body = await page_text(page)
    if "Total:" not in body:
        await save_debug(page, "easypark-period-search-no-total")
        raise RuntimeError("EasyPark viste ikke total etter periodesøk.")


def monthly_periods(year: int, end_day: date | None = None) -> list[tuple[date, date]]:
    today = datetime.now(LOCAL_TZ).date()
    last_allowed = min(end_day or today, today)
    periods: list[tuple[date, date]] = []
    month_start = date(year, 1, 1)
    while month_start <= last_allowed and month_start.year == year:
        next_month = date(year + 1, 1, 1) if month_start.month == 12 else date(year, month_start.month + 1, 1)
        month_end = min(next_month - timedelta(days=1), last_allowed)
        periods.append((month_start, month_end))
        month_start = next_month
    return periods


def post_to_fibaro10(path: Path) -> dict[str, Any]:
    if not FIBARO10_USERNAME or not FIBARO10_PASSWORD:
        raise RuntimeError("FIBARO10_USERNAME/FIBARO10_PASSWORD mangler.")
    with path.open("rb") as file_handle:
        response = requests.post(
            f"{FIBARO10_BASE_URL}/api/parkering/import-csv",
            params={"username": FIBARO10_USERNAME, "password": FIBARO10_PASSWORD},
            files={"file": (path.name, file_handle, "text/csv")},
            timeout=180,
        )
    if response.status_code >= 400:
        raise RuntimeError(f"Fibaro10 import feilet: HTTP {response.status_code}: {response.text[:500]}")
    return response.json()


def report_failure_to_fibaro10(started_at: str, message: str) -> None:
    if not FIBARO10_USERNAME or not FIBARO10_PASSWORD:
        return
    try:
        requests.post(
            f"{FIBARO10_BASE_URL}/api/import-status/report",
            params={"username": FIBARO10_USERNAME, "password": FIBARO10_PASSWORD},
            json={
                "job_name": "easypark_parking_import",
                "ok": False,
                "source": "EasyPark downloader",
                "started_at": started_at,
                "finished_at": fibaro10_datetime_iso(),
                "records_imported": 0,
                "records_total": 0,
                "message": message,
                "raw": {"component": "easypark_downloader"},
            },
            timeout=30,
        )
    except Exception:
        pass


async def run_download_import(
    from_day: date | None = None,
    to_day: date | None = None,
    force_login: bool = False,
) -> dict[str, Any]:
    validate_period(from_day, to_day)
    period = period_label(from_day, to_day)
    set_state(running=True, last_action="starting", last_error=None, last_period=period)
    started = fibaro10_datetime_iso()
    try:
        async with async_playwright() as playwright:
            if force_login:
                set_state(last_action="logout_before_login", last_period=period)
                await try_logout_existing_session(playwright)
                set_state(last_action="refresh_login", last_period=period)
                write_auth_state(
                    last_reset_at=utcnow_iso(),
                    last_reset_reason="scheduled logout/login without profile reset",
                    last_logout_at=utcnow_iso(),
                    last_login_at=None,
                )

            launch_options: dict[str, Any] = {}
            if EDGE_EXECUTABLE_PATH and Path(EDGE_EXECUTABLE_PATH).exists():
                launch_options["executable_path"] = EDGE_EXECUTABLE_PATH

            context = await playwright.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                headless=HEADLESS,
                accept_downloads=True,
                downloads_path=str(DOWNLOAD_DIR),
                viewport={"width": 1365, "height": 900},
                locale="en-US",
                timezone_id="Europe/Oslo",
                **launch_options,
            )
            page = context.pages[0] if context.pages else await context.new_page()
            try:
                set_state(last_action="login")
                login_performed = await ensure_logged_in(page)
                if login_performed:
                    set_state(last_action="login_completed")
                if from_day and to_day:
                    set_state(last_action="set_period", last_period=period)
                    await set_date_range(page, from_day, to_day)
                    set_state(last_action="download", last_period=period)
                    file_path = await download_report(page)
                else:
                    set_state(last_action="download")
                    file_path = await download_report(page)
            finally:
                try:
                    await context.close()
                except Exception:
                    pass

        set_state(last_action="import")
        import_result = post_to_fibaro10(file_path)
        result = {"ok": True, "started_at": started, "period": period, "file": str(file_path), "import": import_result}
        set_state(
            running=False,
            last_success_at=utcnow_iso(),
            last_error=None,
            last_file=str(file_path),
            last_import=import_result,
            last_period=period,
            last_action="done",
        )
        return result
    except Exception as exc:
        set_state(running=False, last_error=str(exc), last_action="error", last_period=period)
        report_failure_to_fibaro10(started, str(exc))
        raise


async def run_once(from_day: date | None = None, to_day: date | None = None) -> dict[str, Any]:
    async with lock:
        return await run_download_import(from_day, to_day)


def should_force_login_now() -> bool:
    now = datetime.now(LOCAL_TZ)
    for hour, minute in parse_run_times(FORCE_LOGIN_TIMES):
        if now.hour == hour and now.minute == minute:
            return True
    return False


async def run_scheduled_once() -> dict[str, Any]:
    from_day, to_day = scheduled_period()
    async with lock:
        return await run_download_import(from_day, to_day, force_login=should_force_login_now())


async def run_backfill_year(year: int, end_day: date | None = None) -> dict[str, Any]:
    async with lock:
        results: list[dict[str, Any]] = []
        set_state(running=True, last_action="backfill_start", last_error=None, last_period=str(year))
        for from_day, to_day in monthly_periods(year, end_day):
            set_state(last_action="backfill_period", last_period=period_label(from_day, to_day))
            results.append(await run_download_import(from_day, to_day, force_login=False))
        totals = {
            "periods": len(results),
            "inserted": sum(int(item.get("import", {}).get("inserted") or 0) for item in results),
            "updated": sum(int(item.get("import", {}).get("updated") or 0) for item in results),
            "unchanged": sum(int(item.get("import", {}).get("unchanged") or 0) for item in results),
            "skipped": sum(int(item.get("import", {}).get("skipped") or 0) for item in results),
            "total": sum(int(item.get("import", {}).get("total") or 0) for item in results),
        }
        set_state(running=False, last_action="backfill_done", last_period=str(year))
        return {"ok": True, "year": year, "totals": totals, "results": results}


async def worker_loop() -> None:
    if RUN_ON_START:
        try:
            await run_scheduled_once()
        except Exception:
            pass
    while True:
        await asyncio.sleep(seconds_until_next_run())
        try:
            await run_scheduled_once()
        except Exception:
            pass


def seconds_until_next_run() -> int:
    schedule_times = parse_run_times(RUN_TIMES)
    if schedule_times:
        now = datetime.now(LOCAL_TZ)
        candidates = [
            now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            for hour, minute in schedule_times
        ]
        future = [candidate for candidate in candidates if candidate > now]
        target = min(future) if future else min(candidates) + timedelta(days=1)
        return max(60, int((target - now).total_seconds()))
    if RUN_EVERY_HOUR:
        now = datetime.now(LOCAL_TZ)
        target = now.replace(minute=RUN_MINUTE, second=0, microsecond=0)
        if target <= now:
            target += timedelta(hours=1)
        return max(60, int((target - now).total_seconds()))
    if RUN_AT:
        match = re.match(r"^(\d{1,2}):(\d{2})$", RUN_AT)
        if match:
            hour = max(0, min(23, int(match.group(1))))
            minute = max(0, min(59, int(match.group(2))))
            now = datetime.now(LOCAL_TZ)
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return max(60, int((target - now).total_seconds()))
    return max(1, RUN_INTERVAL_MINUTES) * 60


@app.on_event("startup")
async def startup() -> None:
    for path in (DATA_DIR, PROFILE_DIR, DOWNLOAD_DIR, ARTIFACT_DIR):
        path.mkdir(parents=True, exist_ok=True)
    global worker_task
    worker_task = asyncio.create_task(worker_loop())


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "running": state["running"], "last_success_at": state["last_success_at"], "last_error": state["last_error"]}


@app.get("/status")
async def status() -> dict[str, Any]:
    return {
        **state,
        "auth": read_auth_state(),
        "schedule": {
            "run_times": [f"{hour:02d}:{minute:02d}" for hour, minute in parse_run_times(RUN_TIMES)],
            "run_at": RUN_AT,
            "run_every_hour": RUN_EVERY_HOUR,
            "force_login_times": [f"{hour:02d}:{minute:02d}" for hour, minute in parse_run_times(FORCE_LOGIN_TIMES)],
            "recent_days": RECENT_DAYS,
        },
    }


@app.post("/sync-now")
async def sync_now(
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    force_login: bool = Query(default=False),
) -> dict[str, Any]:
    if lock.locked():
        return {"status": "busy", **state}
    try:
        async with lock:
            return await run_download_import(parse_iso_date(from_date), parse_iso_date(to_date), force_login=force_login)
    except Exception as exc:
        return {"status": "error", "detail": str(exc), **state}


@app.post("/sync-period")
async def sync_period(
    from_date: str = Query(...),
    to_date: str = Query(...),
    force_login: bool = Query(default=False),
) -> dict[str, Any]:
    if lock.locked():
        return {"status": "busy", **state}
    try:
        async with lock:
            return await run_download_import(parse_iso_date(from_date), parse_iso_date(to_date), force_login=force_login)
    except Exception as exc:
        return {"status": "error", "detail": str(exc), **state}


@app.post("/backfill-year")
async def backfill_year(
    year: int = Query(..., ge=2017, le=2100),
    end_date: str | None = Query(default=None),
) -> dict[str, Any]:
    if lock.locked():
        return {"status": "busy", **state}
    try:
        return await run_backfill_year(year, parse_iso_date(end_date))
    except Exception as exc:
        return {"status": "error", "detail": str(exc), **state}
