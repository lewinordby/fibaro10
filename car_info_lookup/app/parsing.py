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


class VehicleHtmlParser(HTMLParser):
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


def extract_label_value_specs(html_text: str) -> dict[str, str]:
    facts: dict[str, str] = {}
    pattern = re.compile(
        r'<span[^>]*class="[^"]*\blabel\b[^"]*"[^>]*>(?P<label>.*?)</span>\s*'
        r'<span[^>]*class="[^"]*\bvalue\b[^"]*"[^>]*>(?P<value>.*?)</span>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(html_text):
        label = strip_tags(match.group("label")).strip(" :")
        value = strip_tags(match.group("value")).strip(" :")
        if not label or not value or len(label) > 100 or len(value) > 240:
            continue
        if value.casefold() in {"logga in", "ok\u00e4nd", "unknown"}:
            continue
        facts[label] = value
    return facts


def field_from_facts(facts: dict[str, str], *labels: str) -> str | None:
    normalized = {normalize_text(key).casefold(): value for key, value in facts.items()}
    asciiish = {re.sub(r"[^a-z0-9]+", "", key.casefold()): value for key, value in normalized.items()}
    for label in labels:
        normalized_label = normalize_text(label).casefold()
        value = normalized.get(normalized_label)
        if not value:
            value = asciiish.get(re.sub(r"[^a-z0-9]+", "", normalized_label))
        if value:
            return value
    for key, value in normalized.items():
        if any(label.casefold() in key for label in labels):
            return value
    return None


def split_model_year(value: Any) -> str | None:
    text = normalize_text(value)
    years = re.findall(r"(?:19|20)\d{2}", text)
    return years[-1] if years else None


def parse_biluppgifter_description(description: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    text = normalize_text(description)
    match = re.search(
        r"^[A-Z0-9]+\s+(?:\u00e4r|er)\s+en\s+(?P<color>.+?)\s+(?P<vehicle_type>.+?)\s+av\s+"
        r"\u00e5rsmodell\s+(?P<year>20\d{2}|19\d{2})",
        text,
        re.IGNORECASE,
    )
    if match:
        fields["color"] = normalize_text(match.group("color"))
        fields["vehicle_type"] = normalize_text(match.group("vehicle_type"))
        fields["model_year"] = match.group("year")
    return fields


def parse_biluppgifter_html(plate: str, url: str, html_text: str, text_limit: int = 12000) -> dict[str, Any]:
    parser = VehicleHtmlParser()
    parser.feed(html_text)
    title = parser.meta.get("og:title") or parser.title
    description = parser.meta.get("og:description") or parser.meta.get("description") or ""
    facts = extract_label_value_specs(html_text)
    fields = parse_biluppgifter_description(description)

    make = field_from_facts(facts, "Fabrikat")
    model = field_from_facts(facts, "Variant") or field_from_facts(facts, "Modell")
    h1_candidates = [item for item in parser.h1 if re.search(r"\b(?:19|20)\d{2}\b", item) or re.search(r"\d+\s*hk", item, re.IGNORECASE)]
    h1 = h1_candidates[0] if h1_candidates else (parser.h1[-1] if parser.h1 else None)
    h1_title = re.sub(r",\s*\d+\s*hk.*$", "", h1 or "", flags=re.IGNORECASE).strip()
    if make and model:
        fields["vehicle_title"] = f"{make} {model}"
    elif h1_title:
        fields["vehicle_title"] = h1_title
    else:
        fields["vehicle_title"] = title

    fact_power = field_from_facts(facts, "Motoreffekt")
    h1_power = re.search(r"(\d{2,4})\s*hk", h1 or "", re.IGNORECASE)
    if fact_power:
        fields["power"] = fact_power
    elif h1_power:
        fields["power"] = f"{h1_power.group(1)} HK"
    fields.setdefault("model_year", split_model_year(field_from_facts(facts, "Fordons\u00e5r / Modell\u00e5r")) or split_model_year(h1))

    field_map = {
        "first_registered": ("F\u00f6rst registrerad",),
        "first_registration_sweden": ("Trafik i Sverige",),
        "latest_owner_change": ("Senaste \u00e4garbyte",),
        "vehicle_type": ("Typ",),
        "body_type": ("Kaross",),
        "color": ("F\u00e4rg",),
        "registration_status": ("Status",),
        "mileage": ("M\u00e4tarst\u00e4llning (besiktning)", "M\u00e4tarst\u00e4llning"),
        "inspection_valid_to": ("N\u00e4sta besiktning senast",),
        "last_inspected": ("Senast besiktigad",),
        "fuel": ("Drivmedel", "Br\u00e4nsle"),
        "transmission": ("V\u00e4xell\u00e5da",),
        "power": ("Motoreffekt",),
        "engine": ("Motorvolym",),
        "drivetrain": ("Fyrhjulsdrift",),
        "classification": ("Fordonskategori EU",),
        "seats": ("Passagerare",),
        "vin": ("Chassinr / VIN",),
        "tax": ("\u00c5rlig skatt",),
        "leased": ("Leasad",),
        "imported": ("Import / Inf\u00f6rsel",),
        "fuel_consumption_combined": ("Elf\u00f6rbrukning Blandad", "F\u00f6rbrukning"),
        "range_wltp": ("R\u00e4ckvidd",),
    }
    for key, labels in field_map.items():
        fields.setdefault(key, field_from_facts(facts, *labels))
    if fields.get("drivetrain") == "Ja":
        fields["drivetrain"] = "Fyrhjulsdrift"

    compact = compact_plate(plate)
    confirmed_swedish = is_swedish_license_plate(compact) and (
        "biluppgifter.se/fordon/" in url.lower()
        and (facts.get("Registreringsnummer") == compact or compact in normalize_text(title).upper())
        and bool(facts)
    )
    return {
        "provider": "biluppgifter",
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
    return (
        status_code == 429
        or ("just a moment" in text and "enable javascript and cookies" in text)
        or "f\u00f6r m\u00e5nga f\u00f6rfr\u00e5gningar" in text
        or "too many requests" in text
    )
