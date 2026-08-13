from typing import Any, Mapping


CLEANING_TYPE_LABELS = {
    "vacuum": "Støvsuging",
    "mop": "Vask",
    "vacuum_mop": "Støvsug + vask",
}

FAN_OPTIONS = {
    105: "Av",
    101: "Stille",
    102: "Balansert",
    103: "Turbo",
    104: "Maks",
    108: "Maks+",
}

WATER_OPTIONS = {
    200: "Av",
    201: "Lav",
    202: "Medium",
    203: "Høy",
}

MOP_OPTIONS = {
    300: "Standard",
    301: "Dyp",
    303: "Dyp+",
    304: "Hurtig",
}

DEFAULT_CLEANING_PROFILES = (
    {
        "slug": "vacuum-normal",
        "name": "Vanlig støvsuging",
        "description": "Daglig støvsuging med balansert sugekraft og én runde.",
        "cleaning_type": "vacuum",
        "fan_power": 102,
        "water_box_mode": 200,
        "mop_mode": 300,
        "repeat": 1,
    },
    {
        "slug": "vacuum-intensive",
        "name": "Intensiv støvsuging",
        "description": "Maksimal sugekraft og to runder for grundigere støvsuging.",
        "cleaning_type": "vacuum",
        "fan_power": 104,
        "water_box_mode": 200,
        "mop_mode": 300,
        "repeat": 2,
    },
    {
        "slug": "mop-normal",
        "name": "Vanlig vask",
        "description": "Standard vask, medium vannmengde og én runde uten støvsuging.",
        "cleaning_type": "mop",
        "fan_power": 105,
        "water_box_mode": 202,
        "mop_mode": 300,
        "repeat": 1,
    },
    {
        "slug": "mop-intensive",
        "name": "Intensiv vask",
        "description": "Dyp+ vask, høy vannmengde og to runder uten støvsuging.",
        "cleaning_type": "mop",
        "fan_power": 105,
        "water_box_mode": 203,
        "mop_mode": 303,
        "repeat": 2,
    },
    {
        "slug": "vacuum-mop-normal",
        "name": "Vanlig kombi",
        "description": "Balansert støvsuging og standard vask i én runde.",
        "cleaning_type": "vacuum_mop",
        "fan_power": 102,
        "water_box_mode": 202,
        "mop_mode": 300,
        "repeat": 1,
    },
    {
        "slug": "vacuum-mop-intensive",
        "name": "Intensiv kombi",
        "description": "Maksimal støvsuging, Dyp+ vask, høy vannmengde og to runder.",
        "cleaning_type": "vacuum_mop",
        "fan_power": 104,
        "water_box_mode": 203,
        "mop_mode": 303,
        "repeat": 2,
    },
)


def option_rows(options: Mapping[int, str]) -> list[dict[str, Any]]:
    return [{"value": value, "label": label} for value, label in options.items()]


def cleaning_profile_options(model: str | None = None) -> dict[str, Any]:
    # a51 and a75 use the same deterministic values below. Custom and Smart
    # require additional vendor parameters and are intentionally not exposed.
    return {
        "model": model,
        "cleaningTypes": [
            {"value": value, "label": label} for value, label in CLEANING_TYPE_LABELS.items()
        ],
        "fanPower": option_rows(FAN_OPTIONS),
        "waterBoxMode": option_rows(WATER_OPTIONS),
        "mopMode": option_rows(MOP_OPTIONS),
        "repeat": [
            {"value": 1, "label": "1 runde"},
            {"value": 2, "label": "2 runder"},
            {"value": 3, "label": "3 runder"},
        ],
        "excludedModes": [
            "Tilpassede og smarte Roborock-moduser krever egne vendorparametere og brukes ikke i faste profiler.",
        ],
    }


def validate_cleaning_profile(values: Mapping[str, Any]) -> dict[str, Any]:
    cleaning_type = str(values.get("cleaning_type") or "").strip().lower()
    if cleaning_type not in CLEANING_TYPE_LABELS:
        raise ValueError("Velg støvsuging, vask eller støvsuging med vask")

    try:
        fan_power = int(values.get("fan_power"))
        water_box_mode = int(values.get("water_box_mode"))
        mop_mode = int(values.get("mop_mode"))
        repeat = int(values.get("repeat"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Profilen inneholder en ugyldig Roborock-innstilling") from exc

    if fan_power not in FAN_OPTIONS:
        raise ValueError("Ugyldig sugekraft")
    if water_box_mode not in WATER_OPTIONS:
        raise ValueError("Ugyldig vannmengde")
    if mop_mode not in MOP_OPTIONS:
        raise ValueError("Ugyldig vaskemønster")
    if repeat not in {1, 2, 3}:
        raise ValueError("Antall runder må være mellom 1 og 3")
    if cleaning_type == "vacuum" and (fan_power == 105 or water_box_mode != 200):
        raise ValueError("Støvsuging krever aktiv suging og vannmengde Av")
    if cleaning_type == "mop" and (fan_power != 105 or water_box_mode == 200):
        raise ValueError("Vask krever sugekraft Av og aktiv vannmengde")
    if cleaning_type == "vacuum_mop" and (fan_power == 105 or water_box_mode == 200):
        raise ValueError("Kombinert renhold krever både aktiv suging og vann")

    return {
        "cleaning_type": cleaning_type,
        "fan_power": fan_power,
        "water_box_mode": water_box_mode,
        "mop_mode": mop_mode,
        "repeat": repeat,
    }


def cleaning_profile_summary(values: Mapping[str, Any]) -> str:
    settings = validate_cleaning_profile(values)
    parts = [CLEANING_TYPE_LABELS[settings["cleaning_type"]]]
    if settings["fan_power"] != 105:
        parts.append(FAN_OPTIONS[settings["fan_power"]])
    if settings["water_box_mode"] != 200:
        parts.extend(
            [MOP_OPTIONS[settings["mop_mode"]], f"{WATER_OPTIONS[settings['water_box_mode']]} vann"]
        )
    parts.append(f"{settings['repeat']} runde" if settings["repeat"] == 1 else f"{settings['repeat']} runder")
    return " · ".join(parts)
