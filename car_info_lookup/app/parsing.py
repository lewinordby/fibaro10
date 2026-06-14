from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from typing import Any


SWEDISH_LICENSE_PLATE_RE = re.compile(r"^[A-HJ-PR-UW-Z]{3}[0-9]{2}([0-9]|[A-HJ-NPR-UW-Z])$")


def compact_plate(value: str | None) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value or "").upper()


def is_swedish_license_plate(value: str | None) -> bool:
    return bool(SWEDISH_LICENSE_PLATE_RE.fullmatch(compact_plate(value)))


class CarInfoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta: dict[str, str] = {}
        self.h1: list[str] = []
        self.text_parts: list[str] = []
        self.json_ld: list[Any] = []
        self._capture: str | None = None
        self._capture_parts: list[str] = []
        self._script_type = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key.lower(): value or "" for key, value in attrs}
        if tag == "title":
            self._capture = "title"
            self._capture_parts = []
        elif tag == "h1":
            self._capture = "h1"
            self._capture_parts = []
        elif tag == "meta":
            key = attr.get("name") or attr.get("property")
            content = attr.get("content")
            if key and content:
                self.meta[key.lower()] = content.strip()
        elif tag == "script":
            self._script_type = attr.get("type", "").lower()
            if self._script_type == "application/ld+json":
                self._capture = "jsonld"
                self._capture_parts = []

    def handle_endtag(self, tag: str) -> None:
        if self._capture == "title" and tag == "title":
            self.title = normalize_text(" ".join(self._capture_parts))
            self._capture = None
        elif self._capture == "h1" and tag == "h1":
            text = normalize_text(" ".join(self._capture_parts))
            if text:
                self.h1.append(text)
            self._capture = None
        elif self._capture == "jsonld" and tag == "script":
            raw = "\n".join(self._capture_parts).strip()
            if raw:
                try:
                    self.json_ld.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass
            self._capture = None
            self._script_type = ""

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._capture_parts.append(data)
        text = normalize_text(data)
        if text:
            self.text_parts.append(text)


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def strip_tags(value: str) -> str:
    return normalize_text(re.sub(r"<[^>]+>", " ", value))


def extract_specs(html_text: str) -> dict[str, str]:
    facts: dict[str, str] = {}
    pattern = re.compile(r'<span[^>]*class="[^"]*\bsptitle\b[^"]*"[^>]*>(?P<label>.*?)</span>', re.IGNORECASE | re.DOTALL)
    matches = list(pattern.finditer(html_text))
    for index, match in enumerate(matches):
        label = strip_tags(match.group("label"))
        if not label or len(label) > 80:
            continue
        next_start = matches[index + 1].start() if index + 1 < len(matches) else min(len(html_text), match.end() + 1200)
        tail = html_text[match.end():next_start]
        stop = re.split(r"</div>\s*</div>", tail, maxsplit=1, flags=re.IGNORECASE | re.DOTALL)[0]
        value = strip_tags(stop)
        value = re.sub(r"\b(Value from|Click for|Information is missing|Explanation:).*$", "", value, flags=re.IGNORECASE).strip(" :-")
        if value and value.lower() != label.lower() and len(value) <= 240:
            facts[label] = value
    return facts


def first_value(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def field_from_facts(facts: dict[str, str], *labels: str) -> str | None:
    normalized = {normalize_text(key).casefold(): value for key, value in facts.items()}
    for label in labels:
        value = normalized.get(normalize_text(label).casefold())
        if value:
            return value
    for key, value in normalized.items():
        if any(label.casefold() in key for label in labels):
            return value
    return None


def parse_description(description: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    text = normalize_text(description)
    match = re.search(r"^[A-Z0-9]+\s+(?:is|är)\s+(?:a|en|ett)\s+(?P<color>\w+)\s+(?P<rest>.+?)\s+(?:from|från)\s+(?P<year>20\d{2}|19\d{2})", text, re.IGNORECASE)
    if match:
        fields["color"] = match.group("color")
        fields["vehicle_title"] = normalize_text(match.group("rest"))
        fields["model_year"] = match.group("year")
    power = re.search(r"(\d{2,4})\s*(?:hp|hk)", text, re.IGNORECASE)
    if power:
        fields["power"] = f"{power.group(1)} hp"
    if re.search(r"electric|elbil|el\s", text, re.IGNORECASE):
        fields["fuel"] = "Elektrisk"
    elif re.search(r"hybrid|laddhybrid", text, re.IGNORECASE):
        fields["fuel"] = "Hybrid"
    elif re.search(r"diesel", text, re.IGNORECASE):
        fields["fuel"] = "Diesel"
    elif re.search(r"petrol|bensin", text, re.IGNORECASE):
        fields["fuel"] = "Bensin"
    if re.search(r"automatic|automat", text, re.IGNORECASE):
        fields["transmission"] = "Automat"
    status = re.search(r"(?:I trafik|In traffic):\s*([^\.]+)", text, re.IGNORECASE)
    if status:
        fields["registration_status"] = normalize_text(status.group(1))
    return fields


def parse_car_info_html(plate: str, url: str, html_text: str, text_limit: int = 12000) -> dict[str, Any]:
    parser = CarInfoParser()
    parser.feed(html_text)
    title = parser.meta.get("og:title") or parser.title
    description = parser.meta.get("og:description") or parser.meta.get("description") or ""
    facts = extract_specs(html_text)
    fields = parse_description(description)
    vehicle_title = fields.get("vehicle_title")
    title_match = re.search(r"^[A-Z0-9]+\s*-\s*(?P<title>.+?)(?:,\s*(?P<year>20\d{2}|19\d{2}))?$", title)
    if title_match:
        vehicle_title = vehicle_title or normalize_text(title_match.group("title"))
        fields.setdefault("model_year", title_match.group("year"))
    fields["vehicle_title"] = first_value(vehicle_title, parser.h1[0] if parser.h1 else None, title)
    field_map = {
        "first_registered": ("First registered", "Registered", "Registrerad", "Första registrering", "Registreringsdatum"),
        "vehicle_type": ("Vehicle type", "Body type", "Kaross", "Fordonstyp", "Biltyp"),
        "color": ("Color", "Colour", "Färg"),
        "mileage": ("Mileage", "Odometer", "Mätarställning", "Mil"),
        "inspection_valid_to": ("Inspection valid to", "Besiktning giltig till", "Besiktigas senast", "Kontrollfrist"),
        "engine": ("Engine", "Motor"),
        "fuel": ("Fuel", "Drivstoff", "Bränsle"),
        "transmission": ("Transmission", "Växellåda", "Girkasse"),
        "power": ("Power", "Effekt"),
    }
    for key, labels in field_map.items():
        fields.setdefault(key, field_from_facts(facts, *labels))
    compact = compact_plate(plate)
    confirmed_swedish = is_swedish_license_plate(compact) and (
        "/license-plate/s/" in url.lower()
        or "license_code_S" in html_text
        or "marketCode = \"se\"" in html_text
        or "car.info/en-se" in html_text.lower()
        or "car.info/sv-se" in html_text.lower()
    )
    return {
        "plate": compact,
        "country_code": "S",
        "confirmed_swedish": confirmed_swedish,
        "url": url,
        "title": title,
        "vehicle_title": fields.get("vehicle_title"),
        "description": description,
        "fields": {key: value for key, value in fields.items() if value not in (None, "")},
        "facts": facts,
        "json_ld": parser.json_ld[:3],
        "raw_text_excerpt": "\n".join(parser.text_parts)[:text_limit],
    }


def looks_rate_limited(status_code: int, html_text: str) -> bool:
    text = html_text.casefold()
    return status_code == 429 or "coffee break" in text or "maximum number of searches" in text
