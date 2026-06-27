from typing import Dict


V2_MODULE_LABELS: Dict[str, str] = {
    "omsetning": "Omsetning",
    "parkering": "Parkering",
    "soling": "Soling",
    "energi": "Energi",
    "ventilasjon": "Ventilasjon",
    "lys": "Lys",
    "renhold": "Renhold",
    "admin": "Admin",
}


V2_VIEW_LABELS: Dict[str, Dict[str, str]] = {
    "omsetning": {
        "oversikt": "Oversikt",
        "manedsoversikt": "Månedsoversikt",
        "akkumulert": "Årssammenligning",
        "sammenligning": "Periodesammenligning",
    },
    "parkering": {
        "oversikt": "Oversikt",
        "sammenligning": "Årssammenligning",
        "dagslinje": "Dagslinje",
        "parkeringer": "Parkeringer",
        "kjoretoy": "Kjøretøy",
        "prognose": "Prognose",
        "omrade": "Område",
        "bilstatistikk": "Bilstatistikk",
        "oppgjor": "Oppgjør",
        "oppslag": "Oppslag",
    },
    "soling": {
        "oversikt": "Oversikt",
        "sammenligning": "Årssammenligning",
        "dagslinje": "Dagslinje",
        "enkeltimer": "Enkeltimer",
        "senger": "Senger",
        "medlemmer": "Medlemmer",
        "produkter": "Produkter",
        "prognose": "Prognose",
        "oppgjor": "Oppgjør",
        "statistikk": "Statistikk",
        "detaljer": "Detaljer",
    },
    "energi": {
        "status": "Status",
        "kurser": "Kurser",
        "laster": "Laster",
        "forbruk-per-seng": "Forbruk per seng",
        "elvia": "Elvia",
        "verktoy": "Verktøy",
    },
    "ventilasjon": {
        "dagslogg": "Dagslogg",
        "temp-logg": "Temperatur og fukt",
        "yr-logg": "Yr-logg",
        "hendelser": "Hendelser",
        "innstillinger": "Innstillinger",
    },
    "lys": {
        "dagslogg": "Dagslogg",
        "lux-logging": "Lux-logg",
        "hendelser": "Hendelser",
        "innstillinger": "Innstillinger",
    },
    "renhold": {
        "oversikt": "Oversikt",
        "roboter": "Roboter",
    },
    "admin": {
        "oppgaver": "Oppgaver",
        "datakvalitet": "Datakvalitet",
        "analyse": "Analyse",
        "drift": "Drift",
        "build": "Buildlogg",
        "datakilder": "Datakilder",
        "ai": "AI",
        "teknisk": "Teknisk",
        "brukere": "Brukere",
        "manual": "Manual",
        "verktoy": "Verktøy",
    },
}


def v2_view_label(module: str, view: str) -> str:
    normalized_view = (view or "oversikt").strip().lower()
    label = V2_VIEW_LABELS.get(module, {}).get(normalized_view)
    if label:
        return label
    return normalized_view.replace("-", " ").capitalize()


def v2_module_title(module: str, view: str = "") -> str:
    module_label = V2_MODULE_LABELS.get(module, module.capitalize())
    if not view or view == "oversikt":
        return module_label
    return f"{module_label} · {v2_view_label(module, view)}"
