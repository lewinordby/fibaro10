from typing import Dict


V2_MODULE_LABELS: Dict[str, str] = {
    "omsetning": "Omsetning",
    "parkering": "Parkering",
    "soling": "Soling",
    "koble": "Koble",
    "energi": "Energi",
    "ventilasjon": "Ventilasjon",
    "lys": "Lys",
    "vedlikehold": "Vedlikehold",
    "ideer": "Ideer",
    "renhold": "Renhold",
    "admin": "Admin",
}


V2_VIEW_LABELS: Dict[str, Dict[str, str]] = {
    "omsetning": {
        "oversikt": "Oversikt",
        "sammenligning": "Periodesammenligning",
        "akkumulert": "Årssammenligning",
        "manedsoversikt": "Månedsoversikt",
    },
    "parkering": {
        "oversikt": "Oversikt",
        "sammenligning": "Årssammenligning",
        "dagslinje": "Dagslinje",
        "parkeringer": "Parkeringer",
        "oppgjor": "Oppgjør",
        "prognose": "Prognose",
        "kjoretoy": "Kjøretøy",
        "omrade": "Område",
        "oppslag": "Oppslag",
        "bilstatistikk": "Bilstatistikk",
    },
    "soling": {
        "oversikt": "Oversikt",
        "sammenligning": "Årssammenligning",
        "dagslinje": "Dagslinje",
        "enkeltimer": "Enkeltimer",
        "oppgjor": "Oppgjør",
        "prognose": "Prognose",
        "produkter": "Produkter",
        "senger": "Senger",
        "medlemmer": "Medlemmer",
        "statistikk": "Statistikk",
        "detaljer": "Detaljer",
    },
    "koble": {
        "oversikt": "Oversikt",
        "sun2": "SUN2-kontroll",
        "biltreff": "Biltreff",
        "kandidater": "Kandidater",
        "treffgrunnlag": "Treffgrunnlag",
        "jobb": "Jobb",
    },
    "energi": {
        "status": "Status",
        "elvia-kontroll": "Elvia-kontroll",
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
    "vedlikehold": {
        "oversikt": "Oversikt",
    },
    "ideer": {
        "oversikt": "Oversikt",
        "kontroll": "Kontroll",
        "innsikt": "Innsikt",
        "automatisering": "Automatisering",
        "arbeidsflyt": "Arbeidsflyt",
    },
    "renhold": {
        "oversikt": "Oversikt",
        "roboter": "Roboter",
    },
    "admin": {
        "oppgaver": "Oppgaver",
        "kontroll": "Kontroll",
        "datakvalitet": "Datakvalitet",
        "analyse": "Analyse",
        "drift": "Drift",
        "build": "Buildlogg",
        "datakilder": "Datakilder",
        "systemkart": "Systemkart",
        "owntracks": "OwnTracks",
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
