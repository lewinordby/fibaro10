"""Mobile presentation of the same revenue payload used by the desktop app."""

import asyncio
import json
import math
import os
import re
import urllib.request
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from html import escape
from zoneinfo import ZoneInfo


PERIOD_KEYS = ("today", "week", "month", "year")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_overview(session_token: str) -> dict:
    core_url = os.getenv("FIBARO10_BASE_URL", "http://fibaro10:8110").rstrip("/")
    request = urllib.request.Request(
        core_url + "/api/overview?scope=revenue",
        headers={"X-Session-Token": session_token, "Accept": "application/json"},
    )
    with urllib.request.build_opener(NoRedirect).open(request, timeout=8) as response:
        payload = json.loads(response.read(1_000_000))
    cards = payload.get("statusPeriods") if isinstance(payload, dict) else None
    if not isinstance(cards, list) or len(cards) != len(PERIOD_KEYS):
        raise ValueError("Incomplete revenue overview")
    if not all(isinstance(card, dict) and card.get("key") in PERIOD_KEYS for card in cards):
        raise ValueError("Invalid revenue period")
    if {card["key"] for card in cards} != set(PERIOD_KEYS):
        raise ValueError("Incomplete revenue overview")
    return payload


async def load_overview(session_token: str | None) -> dict | None:
    if not session_token or re.search(r"[\r\n;]", session_token):
        return None
    try:
        return await asyncio.to_thread(read_overview, session_token)
    except (OSError, ValueError, TypeError, KeyError):
        # Never replace an unavailable comparison with independently calculated zeros.
        return None


def number(value):
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (TypeError, ValueError):
        return None


def money(value):
    parsed = number(value)
    if parsed is None:
        return "–"
    # Match Intl.NumberFormat in the desktop app, including amounts ending in .50.
    rounded = Decimal(str(parsed)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{rounded:,}".replace(",", " ") + " kr"


def delta(current, reference):
    current, reference = number(current), number(reference)
    if current is None or reference is None:
        return '<span class="rev-delta">–<small>Ukjent grunnlag</small></span>'
    difference = current - reference
    state = "up" if difference > 0 else "down" if difference < 0 else "equal"
    sign = "+" if difference > 0 else "−" if difference < 0 else ""
    percentage = math.floor(difference / reference * 100 + 0.5) if reference > 0 else None
    percent = f'{"+" if percentage > 0 else ""}{percentage}%' if percentage is not None else "Ingen prosentbasis"
    return f'<span class="rev-delta rev-{state}">{sign}{money(abs(difference))}<small>{percent}</small></span>'


def label(value):
    text = str(value or "Sammenligning")
    text = re.sub(r"^(Sammenlignet med|Tilsvarende datatidspunkt)\s*", "", text, flags=re.I)
    text = re.sub(r"^tilsvarende datatidspunkt\s*", "", text, flags=re.I)
    return text[:1].upper() + text[1:]


def date_time(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo:
            parsed = parsed.astimezone(ZoneInfo("Europe/Oslo"))
        return parsed.strftime("%d.%m kl. %H:%M")
    except (ValueError, TypeError):
        return "ukjent"


def references(period):
    previous = {
        key: period.get("previous" + key[:1].upper() + key[1:])
        for key in ("label", "sol", "parking", "total", "fullLabel", "fullTotal")
    }
    return [previous, *(period.get("extraComparisons") or [])[:1]]


def full_reference(current, reference):
    target = number(reference.get("fullTotal"))
    current = number(current)
    progress = min(100, max(0, current / target * 100)) if current is not None and target and target > 0 else 0
    remaining = "Ukjent grunnlag"
    if target is not None and current is not None:
        remaining = f"{money(target - current)} gjenstår" if current < target else f"{money(current - target)} over referansen"
    name = escape(str(reference.get("fullLabel") or reference.get("label") or "Referanse"))
    return f'''<div class="rev-full-reference">
      <div><span>{name}</span><strong>{money(target)}</strong></div>
      <progress max="100" value="{progress:.2f}" aria-label="Andel av {name}"></progress>
      <small>{remaining}</small>
    </div>'''


def period_card(period):
    key = period["key"]
    total = number(period.get("total"))
    refs = references(period)
    rank = period.get("rank") or {}
    rank_html = (
        f'<span class="rev-rank" title="{escape(str(rank.get("basis") or ""), quote=True)}">{escape(str(rank["label"]))}</span>'
        if rank.get("label") and total is not None and total > 0 else ""
    )
    sun = number(period.get("sol"))
    sun_share = max(0, min(100, sun / total * 100)) if total and sun is not None else 0
    rounded_share = math.floor(sun_share + 0.5)
    shares = (f"{rounded_share}%", f"{100 - rounded_share}%") if total and sun is not None else ("–", "–")
    comparisons = ''.join(f'''<div class="rev-comparison">
      <span>{escape(label(ref.get('label')))}</span>
      {delta(total, ref.get('total'))}
      <small>Da: {money(ref.get('total'))}</small>
    </div>''' for ref in refs)
    source_cells = []
    for source, count_key in (("sol", "solCount"), ("parking", "parkingCount")):
        amount, count = number(period.get(source)), number(period.get(count_key))
        average = money(amount / count) if amount is not None and count and count > 0 else "–"
        count_text = f"{count:,.0f}".replace(",", " ") + " stk" if count is not None else "Ukjent antall"
        source_cells.append(f'<td><strong>{money(amount)}</strong><small>{count_text}</small><small>{average} i snitt</small></td>')
    comparison_rows = ''.join(
        f'<tr><th scope="row">Mot {escape(label(ref.get("label"))[:1].lower() + label(ref.get("label"))[1:])}</th>'
        + ''.join(f'<td>{delta(period.get(source), ref.get(source))}</td>' for source in ('sol', 'parking')) + '</tr>'
        for ref in refs
    )
    update = (
        f'<span>Soling {escape(str(period.get("solAsOfLabel") or "ukjent tidspunkt"))}</span>'
        f'<span>Parkering {escape(str(period.get("parkingAsOfLabel") or "ukjent tidspunkt"))}</span>'
    )
    return f'''<article class="rev-period" id="revenue-{key}" data-period="{key}" data-total="{total}" aria-labelledby="revenue-title-{key}">
      <header class="rev-period-heading"><div><h2 id="revenue-title-{key}">{escape(str(period.get('title') or key))}</h2>{rank_html}</div><strong>{money(total)}</strong></header>
      <div class="rev-updated">{update}</div>
      <div class="rev-share" aria-hidden="true"><span style="width:{sun_share:.3f}%"></span></div>
      <div class="rev-comparisons">{comparisons}</div>
      <table class="rev-sources" aria-label="Fordeling og sammenligninger: {escape(str(period.get('title') or key))}">
        <colgroup><col class="rev-label-column"><col><col></colgroup>
        <thead><tr><th scope="col">Inntektskilde</th><th scope="col" class="rev-sun">Soling <small>{shares[0]}</small></th><th scope="col" class="rev-parking">Parkering <small>{shares[1]}</small></th></tr></thead>
        <tbody><tr><th scope="row">Hittil</th>{''.join(source_cells)}</tr></tbody>
      </table>
      <details class="rev-breakdown" data-state-key="revenue-breakdown-{key}"><summary>Forskjell per inntektskilde</summary>
        <table class="rev-sources" aria-label="Forskjeller for {escape(str(period.get('title') or key))}">
          <colgroup><col class="rev-label-column"><col><col></colgroup>
          <thead><tr><th scope="col">Mot</th><th scope="col" class="rev-sun">Soling</th><th scope="col" class="rev-parking">Parkering</th></tr></thead>
          <tbody>{comparison_rows}</tbody>
        </table>
      </details>
      <footer class="rev-references">{''.join(full_reference(total, ref) for ref in refs)}</footer>
    </article>'''


def render_overview(payload):
    if not payload:
        return '''<section class="rev-unavailable" role="status"><strong>Omsetning er ikke tilgjengelig akkurat nå</strong>
          <p>Kunne ikke hente sammenligningsgrunnlaget. Ingen tall er erstattet med null.</p>
          <a href="/omsetning">Prøv igjen</a></section>'''
    periods = {period['key']: period for period in payload['statusPeriods']}
    parking = next((source for source in payload.get('services', []) if source.get('jobName') == 'easypark_parking_import'), {})
    schedule = f'Neste parkeringsimport: {date_time(parking["nextExpectedAt"])}' if parking.get('nextExpectedAt') else 'Neste parkeringsimport: ukjent'
    return f'''<section class="revenue-dashboard" aria-label="Omsetning dashboard" data-generated-at="{escape(str(payload.get('generatedAt') or ''))}">
      <div class="rev-period-tabs" role="tablist" aria-label="Omsetningsperiode" hidden>
        {''.join(f'<button type="button" role="tab" id="revenue-tab-{key}" aria-controls="revenue-{key}" data-period-tab="{key}">{name}</button>' for key, name in zip(PERIOD_KEYS, ('I dag', 'Uke', 'Måned', 'År')))}
      </div>
      <div class="rev-tools"><span>{schedule}</span><a href="/omsetning/uke">Ukediagram <span aria-hidden="true">↗</span></a></div>
      <p class="rev-basis">Sammenligningene følger siste import for hver inntektskilde.</p>
      <div class="rev-periods">{''.join(period_card(periods[key]) for key in PERIOD_KEYS)}</div>
    </section>'''
