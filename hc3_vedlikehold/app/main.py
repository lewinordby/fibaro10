import base64
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse


APP_TITLE = "HC3 vedlikehold"
HC3_BASE_URL = os.environ.get("HC3_BASE_URL", "http://192.168.1.10").rstrip("/")
HC3_USER = os.environ.get("HC3_USER", "")
HC3_PASS = os.environ.get("HC3_PASS", "")
ENERGY_LOGGER_SCENE_ID = int(os.environ.get("ENERGY_LOGGER_SCENE_ID", "365"))

GROUP_IDS = [237, 305, 333, 332, 331, 335, 336, 337, 328, 334]
GROUP_TONES = {
    237: "vent",
    335: "vent",
    305: "light",
    336: "light",
    333: "sun",
    337: "sun",
    332: "neutral",
    328: "neutral",
    331: "energy",
    334: "energy",
}

app = FastAPI(title=APP_TITLE)


class Hc3Error(RuntimeError):
    pass


def now_text() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def configured() -> bool:
    return bool(HC3_BASE_URL and HC3_USER and HC3_PASS)


def auth_header() -> str:
    token = base64.b64encode(f"{HC3_USER}:{HC3_PASS}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def hc3_request(path: str, method: str = "GET", body: Any = None, timeout: int = 20) -> Any:
    if not configured():
        raise Hc3Error("HC3 er ikke konfigurert. Sjekk .env.")
    data = None
    headers = {"Authorization": auth_header(), "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    url = f"{HC3_BASE_URL}{path}"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            if not raw:
                return {"status": response.status}
            text = raw.decode("utf-8")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"status": response.status, "text": text}
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise Hc3Error(f"HC3 svarte {exc.code}: {message}") from exc
    except urllib.error.URLError as exc:
        raise Hc3Error(f"Fikk ikke kontakt med HC3: {exc}") from exc


def strip_lua_comments(content: str) -> str:
    content = re.sub(r"--\[\[.*?\]\]", "", content, flags=re.S)
    return re.sub(r"--.*", "", content)


def ids_from_quickapp(content: str) -> list[int]:
    clean = strip_lua_comments(content or "")
    ids: list[int] = []
    patterns = [
        r"MAIN(?:_METER)?_ID\s*=\s*(\d+)",
        r"METER_IDS\s*=\s*\{([^}]*)\}",
        r"SUB_SUM_QA_IDS\s*=\s*\{([^}]*)\}",
        r"SUB_IDS\s*=\s*\{([^}]*)\}",
        r"METERS\s*=\s*\{(.*?)\n\}",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, clean, flags=re.S):
            text = match if isinstance(match, str) else match[0]
            if pattern.startswith("MAIN"):
                ids.append(int(text))
            elif "METERS" in pattern:
                ids.extend(int(value) for value in re.findall(r"id\s*=\s*(\d+)", text))
            else:
                ids.extend(int(value) for value in re.findall(r"\b\d+\b", text))
    seen: list[int] = []
    for device_id in ids:
        if device_id not in seen:
            seen.append(device_id)
    return seen


def as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def device_label(device: dict[str, Any]) -> str:
    props = device.get("properties") or {}
    suffix = []
    power = as_float(props.get("power"))
    energy = as_float(props.get("energy"))
    value = props.get("value")
    if power is not None:
        suffix.append(f"{power:g} W")
    if energy is not None:
        suffix.append(f"{energy:g} kWh")
    if power is None and energy is None and value not in (None, ""):
        suffix.append(f"value={value}")
    detail = f" ({', '.join(suffix)})" if suffix else ""
    return f"{device.get('id')} - {device.get('name')}{detail}"


def group_description(group: dict[str, Any], members: list[dict[str, Any]]) -> str:
    lines = [
        "Energi-gruppe dokumentert automatisk.",
        "",
        "Undermålere/grunnlag:",
    ]
    if members:
        lines.extend(f"- {device_label(member)}" for member in members)
    else:
        lines.append("- Ingen undermålere funnet i QuickApp-koden.")
    lines.extend(
        [
            "",
            "Merk: Listen er hentet fra QuickApp-koden og brukes som dokumentasjon i HC3.",
        ]
    )
    return "\n".join(lines)


def load_devices() -> dict[int, dict[str, Any]]:
    devices = hc3_request("/api/devices")
    return {int(device["id"]): device for device in devices}


def load_energy_groups() -> list[dict[str, Any]]:
    devices = load_devices()
    groups = []
    for group_id in GROUP_IDS:
        group = devices.get(group_id, {"id": group_id, "name": "Ukjent"})
        file_data = hc3_request(f"/api/quickApp/{group_id}/files/main")
        member_ids = ids_from_quickapp(file_data.get("content") or "")
        members = [devices[device_id] for device_id in member_ids if device_id in devices]
        missing = [device_id for device_id in member_ids if device_id not in devices]
        groups.append(
            {
                "id": group_id,
                "name": group.get("name") or f"Enhet {group_id}",
                "room_id": group.get("roomID"),
                "tone": GROUP_TONES.get(group_id, "neutral"),
                "member_ids": member_ids,
                "members": members,
                "missing": missing,
                "description": group_description(group, members),
            }
        )
    return groups


def update_group_descriptions() -> dict[str, Any]:
    groups = load_energy_groups()
    updated = []
    for group in groups:
        hc3_request(
            f"/api/devices/{group['id']}",
            method="PUT",
            body={"properties": {"userDescription": group["description"]}},
        )
        updated.append({"id": group["id"], "name": group["name"], "members": len(group["members"])})
    return {"updated": updated, "count": len(updated), "at": now_text()}


def load_energy_scene_status() -> dict[str, Any]:
    scene = hc3_request(f"/api/scenes/{ENERGY_LOGGER_SCENE_ID}")
    debug_messages = []
    try:
        raw = hc3_request("/api/debugMessages?limit=180")
        if isinstance(raw, list):
            debug_messages = raw
        elif isinstance(raw, dict):
            debug_messages = raw.get("messages") or raw.get("data") or []
    except Hc3Error:
        debug_messages = []
    energy_logs = []
    for item in debug_messages:
        text = str(item.get("message") or item.get("txt") or item.get("text") or "")
        tag = str(item.get("tag") or item.get("type") or "")
        if "ENERGI" in tag.upper() or "energi" in text.lower():
            energy_logs.append(
                {
                    "time": item.get("timestamp") or item.get("time") or item.get("created"),
                    "tag": tag,
                    "message": text,
                }
            )
    return {
        "id": ENERGY_LOGGER_SCENE_ID,
        "name": scene.get("name"),
        "enabled": scene.get("enabled"),
        "running_instances": scene.get("runningInstances"),
        "max_running_instances": scene.get("maxRunningInstances"),
        "type": scene.get("type"),
        "last_logs": energy_logs[:12],
    }


def restart_energy_logger() -> dict[str, Any]:
    errors = []
    try:
        hc3_request(f"/api/scenes/{ENERGY_LOGGER_SCENE_ID}/kill", method="POST", timeout=8)
    except Hc3Error as exc:
        errors.append(str(exc))
    result = hc3_request(f"/api/scenes/{ENERGY_LOGGER_SCENE_ID}/execute", method="POST", timeout=8)
    return {"started": True, "result": result, "kill_warnings": errors, "at": now_text()}


def h(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def render_page(message: str | None = None, error: str | None = None) -> str:
    scene_status: dict[str, Any] | None = None
    groups: list[dict[str, Any]] = []
    load_error = error
    try:
        scene_status = load_energy_scene_status()
        groups = load_energy_groups()
    except Exception as exc:
        load_error = str(exc)

    group_cards = []
    for group in groups:
        rows = []
        for member in group["members"]:
            props = member.get("properties") or {}
            rows.append(
                f"""
                <tr>
                    <td>{h(member.get("id"))}</td>
                    <td>{h(member.get("name"))}</td>
                    <td>{h(props.get("power", "-"))}</td>
                    <td>{h(props.get("energy", "-"))}</td>
                </tr>
                """
            )
        if not rows:
            rows.append('<tr><td colspan="4" class="muted">Ingen undermålere funnet.</td></tr>')
        missing = ""
        if group["missing"]:
            missing = f"<p class='warning'>Mangler i HC3: {h(', '.join(map(str, group['missing'])))}</p>"
        group_cards.append(
            f"""
            <article class="card tone-{h(group['tone'])}">
                <div class="card-head">
                    <div>
                        <span class="eyebrow">QuickApp {h(group['id'])}</span>
                        <h2>{h(group['name'])}</h2>
                    </div>
                    <strong class="metric">{len(group['members'])}</strong>
                </div>
                {missing}
                <div class="table-wrap">
                    <table>
                        <thead><tr><th>ID</th><th>Undermåler</th><th>W</th><th>kWh</th></tr></thead>
                        <tbody>{''.join(rows)}</tbody>
                    </table>
                </div>
            </article>
            """
        )

    logs = ""
    if scene_status and scene_status.get("last_logs"):
        logs = "".join(
            f"<li><span>{h(item.get('time'))}</span><strong>{h(item.get('tag'))}</strong>{h(item.get('message'))}</li>"
            for item in scene_status["last_logs"]
        )
    else:
        logs = '<li class="muted">Ingen energilogger funnet i siste debug-utvalg.</li>'

    scene_html = ""
    if scene_status:
        running = scene_status.get("running_instances")
        scene_html = f"""
        <section class="hero-grid">
            <article class="hero-card">
                <span class="eyebrow">HC3</span>
                <h1>Vedlikehold</h1>
                <p>Lokal side for ting som bør kunne kjøres manuelt uten å åpne kode.</p>
                <dl>
                    <dt>Adresse</dt><dd>{h(HC3_BASE_URL)}</dd>
                    <dt>Oppdatert</dt><dd>{h(now_text())}</dd>
                </dl>
            </article>
            <article class="hero-card energy">
                <span class="eyebrow">Energilogg scene {h(scene_status.get('id'))}</span>
                <h2>{h(scene_status.get('name'))}</h2>
                <p>Instanser nå: <strong>{h(running if running is not None else "-")}</strong></p>
                <p>Aktivert: <strong>{'Ja' if scene_status.get('enabled') else 'Nei'}</strong></p>
                <form action="/actions/restart-energy-logger" method="post">
                    <button type="submit">Start scenen på nytt</button>
                </form>
            </article>
        </section>
        """
    else:
        scene_html = """
        <section class="hero-grid">
            <article class="hero-card">
                <span class="eyebrow">HC3</span>
                <h1>Vedlikehold</h1>
                <p>Lokal side for ting som bør kunne kjøres manuelt uten å åpne kode.</p>
            </article>
        </section>
        """

    message_html = f"<div class='toast ok'>{h(message)}</div>" if message else ""
    error_html = f"<div class='toast error'>{h(load_error)}</div>" if load_error else ""

    return f"""<!doctype html>
<html lang="no">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{APP_TITLE}</title>
    <style>
        :root {{
            --bg:#eef2f6; --panel:#fff; --text:#162033; --muted:#667085; --line:#d9e0e8;
            --blue:#4d8bd4; --orange:#db9734; --green:#55a763; --purple:#756489; --red:#c95545;
            --shadow:0 1px 2px rgba(16,24,40,.06),0 12px 32px rgba(16,24,40,.08);
        }}
        * {{ box-sizing:border-box; }}
        body {{ margin:0; font-family:system-ui,-apple-system,Segoe UI,sans-serif; background:var(--bg); color:var(--text); }}
        header {{ position:sticky; top:0; z-index:2; background:rgba(255,255,255,.92); border-bottom:1px solid var(--line); backdrop-filter:blur(10px); }}
        .bar {{ width:min(100% - 1.2rem,1180px); margin:0 auto; min-height:4rem; display:flex; align-items:center; justify-content:space-between; gap:1rem; }}
        .brand {{ display:flex; align-items:center; gap:.7rem; font-weight:900; letter-spacing:0; }}
        .brand-mark {{ width:2.2rem; height:2.2rem; display:grid; place-items:center; border-radius:12px; background:#fff7e8; color:#95600f; border:1px solid #e8c982; }}
        .top-actions {{ display:flex; gap:.5rem; flex-wrap:wrap; justify-content:flex-end; }}
        main {{ width:min(100% - 1.2rem,1180px); margin:0 auto; padding:1rem 0 2.4rem; }}
        .hero-grid {{ display:grid; gap:.85rem; margin-bottom:.9rem; }}
        .hero-card, .card, .log-card {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; box-shadow:var(--shadow); padding:1rem; }}
        .hero-card {{ border-top:4px solid var(--blue); }}
        .hero-card.energy {{ border-top-color:var(--orange); }}
        h1, h2 {{ margin:0; letter-spacing:0; }}
        h1 {{ font-size:1.5rem; }}
        h2 {{ font-size:1rem; }}
        p {{ color:var(--muted); margin:.35rem 0 0; line-height:1.42; }}
        dl {{ display:grid; grid-template-columns:5rem 1fr; gap:.28rem .7rem; margin:.8rem 0 0; }}
        dt {{ color:var(--muted); font-weight:800; }}
        dd {{ margin:0; overflow-wrap:anywhere; }}
        .eyebrow {{ display:block; color:var(--muted); text-transform:uppercase; font-size:.72rem; font-weight:850; letter-spacing:.04em; margin-bottom:.2rem; }}
        button, .button {{ min-height:2.25rem; border-radius:8px; border:1px solid #cc842a; background:var(--orange); color:#fff; font-weight:850; padding:.45rem .78rem; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; justify-content:center; }}
        .button.secondary {{ border-color:var(--line); background:#fff; color:var(--text); }}
        form {{ margin:.8rem 0 0; }}
        .toast {{ border-radius:10px; padding:.7rem .85rem; margin:0 0 .9rem; font-weight:800; }}
        .toast.ok {{ background:#eaf7ed; border:1px solid #b7dfc0; color:#2b6c37; }}
        .toast.error {{ background:#fff0ee; border:1px solid #edb9b0; color:#9c382b; }}
        .section-head {{ display:flex; gap:1rem; align-items:flex-end; justify-content:space-between; margin:1rem 0 .55rem; }}
        .section-head h2 {{ font-size:1.12rem; }}
        .group-grid {{ display:grid; gap:.85rem; }}
        .card {{ border-top:4px solid var(--purple); }}
        .card.tone-light {{ border-top-color:var(--orange); }}
        .card.tone-vent {{ border-top-color:var(--green); }}
        .card.tone-sun {{ border-top-color:var(--blue); }}
        .card.tone-energy {{ border-top-color:var(--orange); }}
        .card-head {{ display:flex; align-items:flex-start; justify-content:space-between; gap:.8rem; margin-bottom:.65rem; }}
        .metric {{ font-size:1.8rem; line-height:1; }}
        .table-wrap {{ overflow:auto; border:1px solid var(--line); border-radius:10px; }}
        table {{ width:100%; border-collapse:collapse; min-width:500px; }}
        th, td {{ padding:.48rem .55rem; border-bottom:1px solid #edf1f6; text-align:left; font-size:.84rem; }}
        th {{ background:#f7f9fb; color:var(--muted); font-size:.74rem; text-transform:uppercase; }}
        tr:last-child td {{ border-bottom:0; }}
        .muted {{ color:var(--muted); }}
        .warning {{ color:#9c382b; background:#fff5f3; border:1px solid #f0c8c1; padding:.45rem .55rem; border-radius:8px; }}
        .log-card ul {{ list-style:none; padding:0; margin:.7rem 0 0; display:grid; gap:.45rem; }}
        .log-card li {{ display:grid; grid-template-columns:9rem 5rem 1fr; gap:.5rem; padding:.45rem 0; border-top:1px solid #edf1f6; font-size:.84rem; }}
        .log-card li:first-child {{ border-top:0; }}
        .log-card li span {{ color:var(--muted); }}
        @media (min-width: 760px) {{
            .hero-grid {{ grid-template-columns:1.1fr .9fr; }}
            .group-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
        }}
        @media (max-width: 620px) {{
            .bar {{ align-items:flex-start; flex-direction:column; padding:.75rem 0; }}
            .top-actions {{ width:100%; justify-content:stretch; }}
            .top-actions .button, .top-actions form, .top-actions button {{ width:100%; }}
            dl {{ grid-template-columns:1fr; }}
            .log-card li {{ grid-template-columns:1fr; gap:.1rem; }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="bar">
            <div class="brand"><span class="brand-mark">P</span><span>HC3 vedlikehold</span></div>
            <div class="top-actions">
                <a class="button secondary" href="/api/status">JSON status</a>
                <a class="button secondary" href="https://fibaro10.onrender.com/energi/status">Fibaro10 energi</a>
            </div>
        </div>
    </header>
    <main>
        {message_html}
        {error_html}
        {scene_html}
        <div class="section-head">
            <div>
                <h2>Energigrupper</h2>
                <p>Disse leses direkte fra QuickApp-koden i HC3.</p>
            </div>
            <form action="/actions/update-descriptions" method="post">
                <button type="submit">Oppdater beskrivelser i HC3</button>
            </form>
        </div>
        <section class="group-grid">
            {''.join(group_cards) if group_cards else '<article class="card"><p class="muted">Ingen energigrupper kunne vises.</p></article>'}
        </section>
        <div class="section-head">
            <div>
                <h2>Siste energilogg fra HC3</h2>
                <p>Brukes for å se at scenen faktisk sender videre.</p>
            </div>
        </div>
        <section class="log-card">
            <ul>{logs}</ul>
        </section>
    </main>
</body>
</html>"""


@app.get("/health")
async def health():
    return {"ok": True, "configured": configured(), "hc3": HC3_BASE_URL}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, message: str | None = None, error: str | None = None):
    return HTMLResponse(render_page(message=message, error=error))


@app.post("/actions/update-descriptions")
async def update_descriptions_action():
    try:
        result = update_group_descriptions()
        return RedirectResponse(
            url="/?message=" + urllib.parse.quote(f"Oppdaterte {result['count']} energigrupper i HC3."),
            status_code=303,
        )
    except Exception as exc:
        return RedirectResponse(url="/?error=" + urllib.parse.quote(str(exc)), status_code=303)


@app.post("/actions/restart-energy-logger")
async def restart_energy_logger_action():
    try:
        restart_energy_logger()
        return RedirectResponse(
            url="/?message=" + urllib.parse.quote("Energilogg-scenen er startet på nytt."),
            status_code=303,
        )
    except Exception as exc:
        return RedirectResponse(url="/?error=" + urllib.parse.quote(str(exc)), status_code=303)


@app.get("/api/status")
async def api_status():
    data = {"configured": configured(), "hc3": HC3_BASE_URL, "checked_at": now_text()}
    try:
        data["scene"] = load_energy_scene_status()
        data["groups"] = [
            {
                "id": group["id"],
                "name": group["name"],
                "members": [{"id": member.get("id"), "name": member.get("name")} for member in group["members"]],
                "missing": group["missing"],
            }
            for group in load_energy_groups()
        ]
        data["ok"] = True
    except Exception as exc:
        data["ok"] = False
        data["error"] = str(exc)
    return JSONResponse(data)


@app.get("/api/energy-groups")
async def api_energy_groups():
    try:
        return {"ok": True, "groups": load_energy_groups()}
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
