"""Static domain definitions; no runtime resources."""

from datetime import timedelta
import re


ENERGY_AGGREGATE_METERS = (
    {
        "key": "heat_pumps",
        "label": "Varmepumper",
        "realtimeId": 237,
        "accumulatedId": 335,
        "description": "Samler varmepumpemalere i HC3.",
        "special": False,
    },
    {
        "key": "lighting",
        "label": "Belysning",
        "realtimeId": 305,
        "accumulatedId": 336,
        "description": "Samler belysningsmalere i HC3.",
        "special": False,
    },
    {
        "key": "massage",
        "label": "Massasje",
        "realtimeId": 333,
        "accumulatedId": 337,
        "description": "Samler massasjerom og tilhorende laster i HC3.",
        "special": False,
    },
    {
        "key": "other",
        "label": "Annet",
        "realtimeId": 332,
        "accumulatedId": 328,
        "description": "Samler andre malte laster i HC3.",
        "special": False,
    },
    {
        "key": "difference",
        "label": "Differanse",
        "realtimeId": 331,
        "accumulatedId": 334,
        "description": "Kontrollsamling: hovedinntak minus de fire ordinare samlingene.",
        "special": True,
    },
)

ENERGY_AGGREGATE_METERS_BY_KEY = {row["key"]: row for row in ENERGY_AGGREGATE_METERS}

ENERGY_AGGREGATE_POWER_MEMBERS = {
    "heat_pumps": (226, 230, 234),
    "lighting": (201, 208, 213, 275, 280, 286, 287, 292, 293, 299, 303, 207, 298, 143, 186, 424, 425, 440),
    "massage": (309, 314, 319, 324, 399),
    "other": (269, 247, 368, 373, 378, 405, 406, 160, 449, 530),
}

ENERGY_AGGREGATE_HC3_MEMBERS = {
    **ENERGY_AGGREGATE_POWER_MEMBERS,
    "difference": (221, 237, 305, 333, 332),
}

ENERGY_AGGREGATE_GROUP_BY_POWER_ID = {
    device_id: group_key
    for group_key, device_ids in ENERGY_AGGREGATE_POWER_MEMBERS.items()
    for device_id in device_ids
}

ENERGY_ACCUMULATED_ID_BY_POWER_ID = {
    226: 226, 230: 230, 234: 234,
    201: 201, 208: 208, 213: 213, 275: 275, 280: 280, 286: 286,
    287: 287, 292: 292, 293: 293, 299: 299, 303: 303, 207: 207,
    298: 298, 143: 143, 186: 186, 424: 424, 425: 425, 440: 440,
    309: 308, 314: 313, 319: 318, 324: 323, 399: 398,
    269: 269, 247: 247, 368: 367, 373: 372, 378: 377, 405: 405,
    406: 406, 160: 160, 449: 449, 530: 529,
}

MOBILE_PREVIEW_SCREENS = [
    {"key": "home", "title": "Forside", "subtitle": "Hovedkort og drift akkurat nå", "source_path": "/"},
    {"key": "soling", "title": "Soling", "subtitle": "Dagens solinger og sammenligninger", "source_path": "/soling"},
    {"key": "parkering", "title": "Parkering", "subtitle": "Dagens parkeringer og EasyPark-status", "source_path": "/parkering"},
    {"key": "omsetning", "title": "Omsetning", "subtitle": "Samlet omsetning og periodekort", "source_path": "/omsetning"},
    {"key": "omsetning-uke", "title": "Omsetning uke", "subtitle": "Mobilt søylediagram for uke", "source_path": "/omsetning/uke"},
    {"key": "energi", "title": "Energi", "subtitle": "Strøm nå og forbruk i dag", "source_path": "/energi"},
    {"key": "temperatur", "title": "Temperatur", "subtitle": "Temperatur og fukt fra mobilappen", "source_path": "/temperatur"},
    {"key": "lys", "title": "Lys", "subtitle": "Lysstatus og siste hendelser", "source_path": "/lys"},
    {"key": "ventilasjon", "title": "Ventilasjon", "subtitle": "Viftestatus og siste hendelser", "source_path": "/ventilasjon"},
]

MOBILE_PREVIEW_MONEY_KEYS = {"omsetning", "omsetning-uke"}

SOLROOM_DOOR_HC3 = {
    1: {"device_id": 459, "hc3_name": "98.0 Rom 1"},
    3: {"device_id": 543, "hc3_name": "148.0 Door Sensor"},
    4: {"device_id": 465, "hc3_name": "101.0 Rom 4"},
    5: {"device_id": 463, "hc3_name": "100.0 Rom 5"},
    6: {"device_id": 469, "hc3_name": "104.0 Rom 6"},
    7: {"device_id": 471, "hc3_name": "105.0 Rom 7"},
    8: {"device_id": 473, "hc3_name": "106.0 Rom 8"},
    9: {"device_id": 475, "hc3_name": "107.0 Rom 9"},
    10: {"device_id": 477, "hc3_name": "108.0 Rom 10"},
    11: {"device_id": 479, "hc3_name": "109.0 Rom 11"},
    12: {"device_id": 539, "hc3_name": "130.0 Door Sensor"},
}

DOOR_SENSOR_CONFIG = [
    *[
        {
            "device_id": SOLROOM_DOOR_HC3.get(index, {}).get("device_id"),
            "device_key": f"door_solrom_{index:02d}",
            "title": f"Solrom {index}",
            "hc3_name": SOLROOM_DOOR_HC3.get(index, {}).get("hc3_name", "Ikke koblet i HC3"),
            "group_key": "solrom",
            "group_title": "Solrom",
            "section_key": "1etg" if index in {1, 2, 3, 9} else "vip" if index in {10, 11, 12} else "2etg",
            "section_title": "1.etg" if index in {1, 2, 3, 9} else "VIP" if index in {10, 11, 12} else "2.etg",
            "sort_order": index,
            "normal_state": "closed",
        }
        for index in range(1, 13)
    ],
    {
        "device_id": 453,
        "device_key": "door_453",
        "title": "Bod/kjøkken",
        "hc3_name": "96.0 bod/kjokken",
        "group_key": "andre",
        "group_title": "Andre dører",
        "section_key": "bygg",
        "section_title": "Bygg",
        "sort_order": 101,
        "normal_state": "closed",
    },
    {
        "device_id": 447,
        "device_key": "door_447",
        "title": "Kjeller luke",
        "hc3_name": "94.0 Kjeller luke",
        "group_key": "andre",
        "group_title": "Andre dører",
        "section_key": "bygg",
        "section_title": "Bygg",
        "sort_order": 102,
        "normal_state": "closed",
    },
    {
        "device_id": 413,
        "device_key": "door_413",
        "title": "Arbeidsrom",
        "hc3_name": "86.0 Arbeidsrom",
        "group_key": "andre",
        "group_title": "Andre dører",
        "section_key": "bygg",
        "section_title": "Bygg",
        "sort_order": 103,
        "normal_state": "closed",
    },
    {
        "device_id": 545,
        "device_key": "door_inngang",
        "title": "Inngang",
        "hc3_name": "149.0 Inngang",
        "group_key": "andre",
        "group_title": "Andre dører",
        "section_key": "bygg",
        "section_title": "Bygg",
        "sort_order": 104,
        "normal_state": "closed",
    },
    {
        "device_id": 483,
        "device_key": "door_massasjestudio",
        "title": "Massasjestudio",
        "hc3_name": "112.0 Massasje",
        "group_key": "andre",
        "group_title": "Andre dører",
        "section_key": "bygg",
        "section_title": "Bygg",
        "sort_order": 105,
        "normal_state": "closed",
    },
    {
        "device_id": 535,
        "device_key": "door_loftluke_massasje",
        "title": "Loftluke massasje",
        "hc3_name": "128.0 Loftluke massasje",
        "group_key": "andre",
        "group_title": "Andre dører",
        "section_key": "bygg",
        "section_title": "Bygg",
        "sort_order": 106,
        "normal_state": "closed",
    },
    {
        "device_id": 489,
        "device_key": "door_vaskerom",
        "title": "Vaskerom",
        "hc3_name": "115.0 Vaskerom",
        "group_key": "andre",
        "group_title": "Andre dører",
        "section_key": "bygg",
        "section_title": "Bygg",
        "sort_order": 107,
        "normal_state": "closed",
    },
    {
        "device_id": 487,
        "device_key": "door_papirlager",
        "title": "Papirlager",
        "hc3_name": "114.0 Papirlager",
        "group_key": "andre",
        "group_title": "Andre dører",
        "section_key": "bygg",
        "section_title": "Bygg",
        "sort_order": 108,
        "normal_state": "closed",
    },
    {
        "device_id": 537,
        "device_key": "door_soppelbod",
        "title": "Søppelbod",
        "hc3_name": "129.0 Door Sensor",
        "group_key": "andre",
        "group_title": "Andre dører",
        "section_key": "bygg",
        "section_title": "Bygg",
        "sort_order": 109,
        "normal_state": "closed",
    },
    {
        "device_id": 493,
        "device_key": "door_vaktmesterlager",
        "title": "Vaktmesterlager",
        "hc3_name": "117.0 Vaktmesterlager",
        "group_key": "andre",
        "group_title": "Andre dører",
        "section_key": "bygg",
        "section_title": "Bygg",
        "sort_order": 110,
        "normal_state": "closed",
    },
    {
        "device_id": 495,
        "device_key": "door_toalett",
        "title": "Toalett",
        "hc3_name": "118.0 Toalett",
        "group_key": "andre",
        "group_title": "Andre dører",
        "section_key": "bygg",
        "section_title": "Bygg",
        "sort_order": 111,
        "normal_state": "closed",
    },
]

DOOR_SENSOR_IDS = [int(item["device_id"]) for item in DOOR_SENSOR_CONFIG if item.get("device_id") is not None]

LIGHT_TIMELINE_DEVICES = [
    {"key": "lyslist", "name": "Lyslist dekor", "sample_attr": "light_lyslist", "legacy_ids": [425, 298]},
    {"key": "reklame", "name": "Reklameplakater", "sample_attr": "light_reklame", "legacy_ids": [427]},
    {"key": "spot_glass_275", "name": "Spot foran glassvegg", "sample_attr": "light_spot_glass_275", "legacy_ids": [275]},
    {"key": "spot_glass_299", "name": "Spot foran massasje", "sample_attr": "light_spot_glass_299", "legacy_ids": [299]},
    {"key": "spot_inngang", "name": "6xspot over inngang", "sample_attr": "light_spot_inngang", "legacy_ids": [424]},
    {"key": "parkering", "name": "Parkeringslys/gatelys", "sample_attr": "light_parkering", "legacy_ids": [440]},
]

VENT_TIMELINE_DEVICES = [
    {"key": "vip_intake", "name": "Innluft VIP", "sample_attr": "fan_vip", "legacy_ids": [511]},
    {"key": "floor_intake", "name": "Innluft 2.etg", "sample_attr": "fan_2etg", "legacy_ids": [160]},
    {"key": "roof_exhaust", "name": "Avtrekk tak/loft", "sample_attr": "fan_tak", "legacy_ids": [134]},
    {"key": "dehumidifier_basement", "name": "Avfukter kjeller", "sample_attr": "fan_avfukter", "legacy_ids": [449]},
]

DAY_ZOOM_OPTIONS = [
    {"key": "all", "label": "Hele døgnet", "start_hour": 0, "end_hour": 24, "ticks": [0, 6, 12, 18, 24]},
    {"key": "night", "label": "Natt 00-06", "start_hour": 0, "end_hour": 6, "ticks": [0, 2, 4, 6]},
    {"key": "day", "label": "Dag 06-24", "start_hour": 6, "end_hour": 24, "ticks": [6, 12, 18, 24]},
]

WEATHER_LABELS = {
    "clearsky": "Klarvær",
    "clearsky_day": "Klarvær",
    "clearsky_night": "Klarvær",
    "clearsky_polartwilight": "Klarvær",
    "fair": "Lettskyet",
    "fair_day": "Lettskyet",
    "fair_night": "Lettskyet",
    "fair_polartwilight": "Lettskyet",
    "partlycloudy": "Delvis skyet",
    "partlycloudy_day": "Delvis skyet",
    "partlycloudy_night": "Delvis skyet",
    "partlycloudy_polartwilight": "Delvis skyet",
    "cloudy": "Skyet",
    "fog": "Tåke",
    "lightrain": "Lett regn",
    "rain": "Regn",
    "heavyrain": "Kraftig regn",
    "lightsnow": "Lett snø",
    "snow": "Snø",
    "heavysnow": "Kraftig snø",
    "sleet": "Sludd",
    "lightsleet": "Lett sludd",
    "thunderstorm": "Torden",
    "rainshowers": "Regnbyger",
    "lightrainshowers": "Lette regnbyger",
    "heavyrainshowers": "Kraftige regnbyger",
    "snowshowers": "Snøbyger",
    "lightsnowshowers": "Lette snøbyger",
    "heavysnowshowers": "Kraftige snøbyger",
}

CONFIG_DEFINITIONS = {
    "lights": {
        "title": "Lysstyring",
        "subtitle": "Terskler, driftstid og forklaring for utelys",
        "theme": "theme-light",
        "settings_path": "/lys/innstillinger",
        "api_path": "/api/config/lights",
        "groups": [
            {
                "title": "Felles drift",
                "description": "Gjelder alle lys unntatt parkeringslys der feltet sier at åpningstid ignoreres.",
                "fields": [
                    {"key": "open_from", "label": "Start før åpning", "type": "time", "default": "06:45", "unit": "", "help": "Tidligste tidspunkt lys som følger åpningstid kan være på."},
                    {"key": "close_at", "label": "Normal av-tid", "type": "time", "default": "23:00", "unit": "", "help": "Standard av-tid for lys som følger åpningstid."},
                    {"key": "entrance_close_at", "label": "Inngang av-tid", "type": "time", "default": "23:20", "unit": "", "help": "6xspot over inngang kan stå litt lenger enn øvrige fasadelys."},
                    {"key": "decision_delay_seconds", "label": "Bekreftelsestid", "type": "int", "default": 120, "unit": "sek", "help": "Lux må bekreftes etter denne forsinkelsen før lys endres."},
                    {"key": "config_poll_minutes", "label": "HC3 henter config", "type": "int", "default": 5, "unit": "min", "help": "Hvor ofte HC3 bør kontrollere om versjon er endret."},
                ],
            },
            {
                "title": "Luxgrenser",
                "description": "På-grense er lav lux. Av-grense er høyere lux for å gi hysterese og unngå flimring.",
                "fields": [
                    {"key": "lyslist_on_lux", "label": "Lyslist på under", "type": "float", "default": 1000, "unit": "lux", "help": "Dekorlys på fasade."},
                    {"key": "lyslist_off_lux", "label": "Lyslist av over", "type": "float", "default": 1500, "unit": "lux", "help": "Må være høyere enn på-grensen."},
                    {"key": "reklame_on_lux", "label": "Reklame på under", "type": "float", "default": 500, "unit": "lux", "help": "Reklameplakater på tegelfasade."},
                    {"key": "reklame_off_lux", "label": "Reklame av over", "type": "float", "default": 700, "unit": "lux", "help": "Må være høyere enn på-grensen."},
                    {"key": "spot_glass_on_lux", "label": "Spot foran på under", "type": "float", "default": 1500, "unit": "lux", "help": "Spot 275 og 299 foran glassveggen."},
                    {"key": "spot_glass_off_lux", "label": "Spot foran av over", "type": "float", "default": 2000, "unit": "lux", "help": "Må være høyere enn på-grensen."},
                    {"key": "spot_inngang_on_lux", "label": "6xspot inngang på under", "type": "float", "default": 100, "unit": "lux", "help": "Behovsstyrt inngangslys."},
                    {"key": "spot_inngang_off_lux", "label": "6xspot inngang av over", "type": "float", "default": 150, "unit": "lux", "help": "Må være høyere enn på-grensen."},
                    {"key": "parkering_on_lux", "label": "Parkering på under", "type": "float", "default": 50, "unit": "lux", "help": "Parkeringslys/gatelys."},
                    {"key": "parkering_off_lux", "label": "Parkering av over", "type": "float", "default": 80, "unit": "lux", "help": "Parkeringslys følger ikke åpningstid."},
                ],
            },
        ],
    },
    "ventilation": {
        "title": "Ventilasjonsstyring",
        "subtitle": "Temperaturgrenser, driftstid og forklaring for vifter",
        "theme": "theme-vent",
        "settings_path": "/ventilasjon/innstillinger",
        "api_path": "/api/config/ventilation",
        "groups": [
            {
                "title": "Drift og sikkerhet",
                "description": "Disse grensene hindrer trekk, undertrykk og unødvendig varmetap.",
                "fields": [
                    {"key": "open_from", "label": "Åpningstid fra", "type": "time", "default": "07:00", "unit": "", "help": "Normal start for ventilasjonslogikk."},
                    {"key": "close_at", "label": "Stenging", "type": "time", "default": "23:00", "unit": "", "help": "Normal stengetid."},
                    {"key": "pre_cooling_from", "label": "Forkjøling fra", "type": "time", "default": "05:30", "unit": "", "help": "Kan brukes på varme dager når ute fortsatt er kaldt."},
                    {"key": "exhaust_stop_before_close_minutes", "label": "Stopp avtrekk før stenging", "type": "int", "default": 60, "unit": "min", "help": "Sparer varme mot natten."},
                    {"key": "mechanical_min_outdoor_temp", "label": "Sperr mekanisk under", "type": "float", "default": 7.0, "unit": "°C", "help": "Avtrekk og innluft stoppes når ute er kaldere enn dette."},
                    {"key": "intake_min_outdoor_temp", "label": "Innluft minimum ute", "type": "float", "default": 10.0, "unit": "°C", "help": "Hindrer kald innblåsing."},
                ],
            },
            {
                "title": "Innluft",
                "description": "Innluft skal bare gå når ute faktisk hjelper. Avtrekk får ikke tvinge varm uteluft inn, bortsett fra ved sikkerhetsvarmt loft.",
                "fields": [
                    {"key": "vip_start_temp", "label": "VIP innluft start", "type": "float", "default": 23.8, "unit": "°C", "help": "VIP-viften vurderer primært VIP-temperatur."},
                    {"key": "vip_stop_temp", "label": "VIP innluft stopp", "type": "float", "default": 23.2, "unit": "°C", "help": "Lavere enn start for hysterese."},
                    {"key": "floor_start_temp", "label": "1./2.etg innluft start", "type": "float", "default": 23.8, "unit": "°C", "help": "2.etg-viften vurderer 1.etg og 2.etg."},
                    {"key": "floor_stop_temp", "label": "1./2.etg innluft stopp", "type": "float", "default": 23.2, "unit": "°C", "help": "Lavere enn start for hysterese."},
                    {"key": "outdoor_cooler_delta", "label": "Ute må være kaldere", "type": "float", "default": 1.5, "unit": "°C", "help": "Ute må være minst så mye kaldere enn sonen."},
                    {"key": "max_indoor_heat_need_temp", "label": "Varmebehov under", "type": "float", "default": 21.5, "unit": "°C", "help": "Under denne temperaturen unngår vi kjølende ventilasjon."},
                ],
            },
            {
                "title": "Avtrekk tak/loft",
                "description": "Avtrekk skal ikke gå bare fordi solsenger er i bruk hvis lokalet trenger varme.",
                "fields": [
                    {"key": "loft_exhaust_start_temp", "label": "Takvifte start loft", "type": "float", "default": 30.0, "unit": "°C", "help": "Starter når loftet er varmt nok og ute ikke er for kaldt."},
                    {"key": "loft_exhaust_stop_temp", "label": "Takvifte stopp loft", "type": "float", "default": 28.0, "unit": "°C", "help": "Stopper lavere enn start for hysterese."},
                    {"key": "indoor_allow_exhaust_temp", "label": "Avtrekk tillatt når inne over", "type": "float", "default": 25.0, "unit": "°C", "help": "Hindrer at varme blåses ut når lokalet er kaldt."},
                    {"key": "sunbed_power_1_threshold_w", "label": "Antatt 1 solseng over", "type": "int", "default": 4000, "unit": "W", "help": "Differanse mellom total og målt øvrig forbruk."},
                    {"key": "sunbed_power_2_threshold_w", "label": "Antatt 2 solsenger over", "type": "int", "default": 12000, "unit": "W", "help": "Brukes for vurdering og logging."},
                    {"key": "afterrun_minutes", "label": "Ettergang", "type": "int", "default": 20, "unit": "min", "help": "Hvor lenge vifter kan gå etter siste tydelige varmebelastning."},
                ],
            },
            {
                "title": "Kjeller og avfukter",
                "description": "Avfukteren styres av fukt i kjeller med hysterese.",
                "fields": [
                    {"key": "basement_humidity_start", "label": "Avfukter på over", "type": "float", "default": 60.0, "unit": "%", "help": "Starter avfukter når kjellerfukt er over denne verdien."},
                    {"key": "basement_humidity_stop", "label": "Avfukter av under", "type": "float", "default": 55.0, "unit": "%", "help": "Stopper avfukter når kjellerfukt er under denne verdien."},
                    {"key": "basement_min_temp", "label": "Sperr under kjellertemp", "type": "float", "default": 5.0, "unit": "°C", "help": "Hindrer drift hvis kjelleren er for kald for trygg avfukting."},
                ],
            },
        ],
    },
}

CONTROL_DEVICES = {
    "lights": {
        "lux_sensor": {"key": "lux_ute", "name": "Luxsensor ute", "role": "sensor"},
        "groups": [
            {
                "key": "lyslist",
                "name": "Lyslist fasade",
                "device_ids": [425, 298],
                "on_lux_key": "lyslist_on_lux",
                "off_lux_key": "lyslist_off_lux",
                "time_from_key": "open_from",
                "time_to_key": "close_at",
                "follows_opening_hours": True,
            },
            {
                "key": "reklame",
                "name": "Reklameplakater tegelfasade",
                "on_lux_key": "reklame_on_lux",
                "off_lux_key": "reklame_off_lux",
                "time_from_key": "open_from",
                "time_to_key": "close_at",
                "follows_opening_hours": True,
            },
            {
                "key": "spot_glass",
                "name": "Spot foran glassvegg",
                "on_lux_key": "spot_glass_on_lux",
                "off_lux_key": "spot_glass_off_lux",
                "time_from_key": "open_from",
                "time_to_key": "close_at",
                "follows_opening_hours": True,
            },
            {
                "key": "spot_inngang",
                "name": "6xspot over inngang",
                "on_lux_key": "spot_inngang_on_lux",
                "off_lux_key": "spot_inngang_off_lux",
                "time_from_key": "open_from",
                "time_to_key": "entrance_close_at",
                "follows_opening_hours": True,
            },
            {
                "key": "parkering",
                "name": "Parkeringslys",
                "on_lux_key": "parkering_on_lux",
                "off_lux_key": "parkering_off_lux",
                "time_from_key": None,
                "time_to_key": None,
                "follows_opening_hours": False,
            },
        ],
    },
    "ventilation": {
        "sensors": {
            "outdoor_temp": {"key": "outdoor_temp", "name": "Utetemperatur"},
            "netatmo_main": {"key": "netatmo_main", "name": "Netatmo hovedenhet"},
            "basement_temp": {"key": "basement_temp", "name": "Kjeller temperatur", "device_id": 444},
            "basement_humidity": {"key": "basement_humidity", "name": "Kjeller fukt", "device_id": 445},
            "passive_intake": {"name": "Pass innluft"},
        },
        "fans": [
            {"key": "vip_intake", "name": "Innluft VIP", "zone": "VIP"},
            {"key": "floor_intake", "name": "Innluft 1./2.etg", "zone": "1.etg/2.etg"},
            {"key": "roof_exhaust", "name": "Takvifte avtrekk", "zone": "Loft"},
            {"key": "dehumidifier_basement", "name": "Avfukter kjeller", "zone": "Kjeller", "device_id": 449},
        ],
    },
}

AXIS_SNAPSHOT_FILENAME_RE = re.compile(r"^axis_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})\.jpg$")

AXIS_SNAPSHOT_ID_RE = re.compile(r"^\d{14}$")

ENERGY_FIBARO_AREAS = [
    {"key": "inntak", "label": "Inntak", "tone": "energy"},
    {"key": "varmepumper", "label": "Varmepumper", "tone": "vent"},
    {"key": "belysning", "label": "Belysning", "tone": "light"},
    {"key": "massasje", "label": "Massasje", "tone": "sun2"},
    {"key": "annet", "label": "Annet", "tone": "status"},
    {"key": "avfukter", "label": "Avfukter", "tone": "vent"},
    {"key": "differanse_beregnet", "label": "Differanse", "tone": "admin"},
]

ENERGY_CIRCUIT_SEED_SOURCE = "kursliste_37.xlsx"

ENERGY_CIRCUIT_SEED_ROWS = [
    {"circuit_no": 1, "description": "SENG ROM 1", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 18, "install_method": "B", "rcd_ma": 30},
    {"circuit_no": 2, "description": "ROM 2 SENG", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 17, "install_method": "B2", "rcd_ma": 30},
    {"circuit_no": 3, "description": "VARMEPUMPE \u00d8ST + stikk loft vip mrk 3.", "breaker_type": "Malthe Win", "breaker_rating_a": 16, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 20, "install_method": "B2", "rcd_ma": 30},
    {"circuit_no": 4, "description": "VARMEPUMPE VEST/OVER HOVEDINNGANG", "breaker_type": "Malthe Win", "breaker_rating_a": 16, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 12, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 5, "description": "TERMINAL/ REGISTRERING OG KREMAUTOMAT", "breaker_type": "Malthe Win", "breaker_rating_a": 16, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 12, "install_method": "A2", "rcd_ma": 30},
    {"circuit_no": 6, "description": "LOFT OVER LAGER/TAVLEROM vip", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 15, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 7, "description": "PARKERINGSAUTOMAT/STIKK LOFT VIP MRK. 7", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 40, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 8, "description": "LOFT NORD (OVER SENG 1+2+3) BOD NOR + TILFLUKTSTR\u00d8M/LAGER", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 40, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 9, "description": "STIKK BODROM VED SOL 7 og 8, STIKK KRYP FRA SOL 9 + STIKK V/DATASKAP BOD SSKAP", "breaker_type": "Malthe Win", "breaker_rating_a": 16, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 18, "install_method": "B2", "rcd_ma": 30, "note": "STIKK MASSAJE (h\u00e5ndskrift)"},
    {"circuit_no": 10, "description": "LYS MIDTEN+STIKK TELLUS+TV NEDE+LOFT SYD", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 40, "install_method": "B2", "rcd_ma": 30},
    {"circuit_no": 11, "description": "LYS SOLROM 1-10 + GANG OPPE", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 43, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 12, "description": "SOL ROM 3", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 13, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 13, "description": "ROM 4 SOL", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 12, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 14, "description": "ROM 5 SOL", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 13, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 15, "description": "ROM 6 SOL", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 15, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 16, "description": "ROM 8 SOL", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 12, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 17, "description": "ROM 7 SOL", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 13, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 18, "description": "ROM 10 SOL", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 12, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 19, "description": "ROM 9 SOL", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 13, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 20, "description": "HOVEDBRYTER 21 TIL 30", "breaker_type": "LAST", "breaker_rating_a": 63, "cable_spec": "3x10+J", "cable_length_m": 1, "install_method": "E"},
    {"circuit_no": 21, "description": "LYS VIP (ROM 11,12,13 OG FELLESAREALE)", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 16, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 22, "description": "STIKK UTVENDIG FOR SKILT P\u00c5 TEGELVEGG", "breaker_type": "Malthe Win", "breaker_rating_a": 15, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 15, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 23, "description": "STIKK OVER VINDUER HOVEDINNGANG + BRUSAUTOMAT", "breaker_type": "Malthe Win", "breaker_rating_a": 15, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 15, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 24, "description": "Parkeringsautomat, plakatlys, front spot vip, 2xgatelys parkering", "status": "mangler vern-data"},
    {"circuit_no": 25, "description": "LOFT 9 OG 10 LYS/STIKK", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 12, "install_method": "C", "rcd_ma": 30, "note": "VASKEMASKIN MAS. (h\u00e5ndskrift)"},
    {"circuit_no": 26, "description": "LYS SSKAP,LAGER,WC-VASK,B\u00d8TTEKOTT (vip)", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 15, "install_method": "C", "rcd_ma": 30, "note": "LYSBAD MAS (h\u00e5ndskrift)"},
    {"circuit_no": 27, "description": "VIFTE VIP, VARMEKABEL TAKRENNE", "breaker_type": "Malthe Win", "breaker_rating_a": 13, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 15, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 28, "description": "STIKK LOFT SYD(EKSTRA)", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 12, "install_method": "C", "rcd_ma": 30, "note": "VARME FOLIE MAS. (h\u00e5ndskrift)"},
    {"circuit_no": 29, "description": "VVBEREDER UNDER ROM 8 + STIKK VIP BOD", "breaker_type": "Malthe Win", "breaker_rating_a": 15, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 15, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 30, "description": "VARMEPUMPE VIP", "breaker_type": "Malthe Win", "breaker_rating_a": 16, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 12, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 31, "description": "BRYTER VARMEKABEL I TAKRENNE", "status": "mangler vern-data"},
    {"circuit_no": 32, "description": "ROM 11 SOL (vip)", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 10, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 33, "description": "ROM 12 SOL (vip)", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 14, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 34, "description": "ROM 13 SOL (vip)", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 16, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 35, "description": "AVTREKKSVIFTE TAK (LOFT SYD OVER ROM 9)", "breaker_type": "Malthe Win", "breaker_rating_a": 16, "breaker_characteristic": "C", "cable_spec": "3x1,5+J", "cable_length_m": 12, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 36, "description": "KOBLINGSUR FOR AVTREKK VIP", "status": "mangler vern-data"},
    {"circuit_no": 37, "description": "HOVEDSIKRING/OVERBELASTNINGSVERN", "breaker_type": "NH", "install_method": "GL", "status": "hovedvern"},
]

ENERGY_ACCUMULATED_KEYS = ["inntak", "varmepumper", "belysning", "massasje", "annet", "avfukter"]

ENERGY_SUB_KEYS = ["varmepumper", "belysning", "massasje", "annet"]

ENERGY_REALTIME_MAX_DELTA_SECONDS = 300

ROOF_EXHAUST_UNMETERED_W = 320.0

SUNBED_ANALYSIS_VENTILATION_MATCH_SECONDS = 180

ENERGY_HC3_HOURLY_DISPLAY_OFFSET = timedelta(0)

ENERGY_HOURLY_COMPARE_FIELDS = [
    "stat_date", "year", "month", "day", "hour", "consumption_kwh", "production_kwh",
    "status", "is_verified", "is_estimated", "is_public_holiday", "use_weekend_prices",
]

YR_FORECAST_ASSIGNMENTS = [
    ("api_updated_at", "api_updated_at"),
    ("last_modified", "last_modified"),
    ("expires_at", "expires_at"),
    ("next_fetch_after", "next_fetch_after"),
    ("age_seconds", "age_seconds"),
    ("forecast_time", "forecast_time"),
    ("symbol_code", "symbol"),
    ("weather_text", "text"),
    ("air_temperature", "air_temperature"),
    ("air_temperature_percentile_10", "air_temperature_percentile_10"),
    ("air_temperature_percentile_90", "air_temperature_percentile_90"),
    ("relative_humidity", "relative_humidity"),
    ("wind_speed", "wind_speed"),
    ("wind_speed_of_gust", "wind_speed_of_gust"),
    ("wind_speed_percentile_10", "wind_speed_percentile_10"),
    ("wind_speed_percentile_90", "wind_speed_percentile_90"),
    ("wind_from_direction", "wind_from_direction"),
    ("cloud_area_fraction", "cloud_area_fraction"),
    ("cloud_area_fraction_high", "cloud_area_fraction_high"),
    ("cloud_area_fraction_medium", "cloud_area_fraction_medium"),
    ("cloud_area_fraction_low", "cloud_area_fraction_low"),
    ("fog_area_fraction", "fog_area_fraction"),
    ("dew_point_temperature", "dew_point_temperature"),
    ("air_pressure_at_sea_level", "air_pressure_at_sea_level"),
    ("ultraviolet_index_clear_sky", "ultraviolet_index_clear_sky"),
    ("precipitation_next_1h", "precipitation_next_1h"),
    ("precipitation_next_1h_min", "precipitation_next_1h_min"),
    ("precipitation_next_1h_max", "precipitation_next_1h_max"),
    ("precipitation_next_6h", "precipitation_next_6h"),
    ("precipitation_next_6h_min", "precipitation_next_6h_min"),
    ("precipitation_next_6h_max", "precipitation_next_6h_max"),
    ("probability_of_precipitation_next_1h", "probability_of_precipitation_next_1h"),
    ("probability_of_precipitation_next_6h", "probability_of_precipitation_next_6h"),
    ("probability_of_precipitation_next_12h", "probability_of_precipitation_next_12h"),
    ("probability_of_thunder_next_1h", "probability_of_thunder_next_1h"),
    ("air_temperature_min_next_6h", "air_temperature_min_next_6h"),
    ("air_temperature_max_next_6h", "air_temperature_max_next_6h"),
    ("symbol_confidence_next_12h", "symbol_confidence_next_12h"),
    ("temp_1h", "temp_1h"),
    ("temp_3h", "temp_3h"),
    ("temp_6h", "temp_6h"),
    ("temp_12h", "temp_12h"),
    ("temp_24h", "temp_24h"),
    ("symbol_1h", "symbol_1h"),
    ("symbol_3h", "symbol_3h"),
    ("symbol_6h", "symbol_6h"),
    ("symbol_12h", "symbol_12h"),
    ("symbol_24h", "symbol_24h"),
    ("temp_min_next_6h", "temp_min_next_6h"),
    ("temp_max_next_6h", "temp_max_next_6h"),
]

AI_CONFIG_KEY = "ai"

PARKING_SUN_LINK_PENDING = "Avventer"

PARKING_SUN_LINK_CONFIRMED = "Bekreftet"

PARKING_SUN_LINK_REJECTED = "Avvist"

PARKING_SUN_LINK_STATUSES = [
    PARKING_SUN_LINK_PENDING,
    PARKING_SUN_LINK_CONFIRMED,
    PARKING_SUN_LINK_REJECTED,
]

PARKING_TIMELINE_ROWS = [
    {"key": "capacity", "label": "Kapasitet", "count": 23},
]

PARKING_TIMELINE_CAPACITY = sum(row["count"] for row in PARKING_TIMELINE_ROWS)

PARKING_OCCUPANCY_SCALE_MAX = 25

PARKING_TIME_WEEKDAYS = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"]

PARKING_TIME_PERIOD_OPTIONS = [
    {"key": "this_month", "label": "Denne måneden"},
    {"key": "this_year", "label": "Dette året"},
    {"key": "last_90_days", "label": "Siste 90 dager"},
    {"key": "previous_month", "label": "Forrige måned"},
    {"key": "last_year", "label": "I fjor"},
    {"key": "custom", "label": "Egendefinert"},
]

PARKING_WEEKLY_AVERAGE_PERIOD_OPTIONS = [
    {"key": "this_year", "label": "Dette året"},
    {"key": "last_12_months", "label": "Siste 12 måneder"},
    {"key": "last_24_months", "label": "Siste 24 måneder"},
    {"key": "last_year", "label": "I fjor"},
    {"key": "custom", "label": "Egendefinert"},
]

MAINTENANCE_TAG_OPTIONS = [
    "Tilstede",
    "Kontroll",
    "Renhold",
    "Teknisk",
    "Vedlikehold",
    "Innkjøp",
    "Leverandør",
    "Parkering",
    "Soling",
    "Energi",
    "Ventilasjon",
    "Lys",
    "Avvik",
    "Oppfølging",
]

MAINTENANCE_STATUS_OPTIONS = ["Utført", "Må følges opp", "Planlagt", "Lukket"]

MAINTENANCE_PRESENCE_OPTIONS = ["Tilstede Sun2", "Fjernarbeid", "Telefon/leverandør"]

MAINTENANCE_TARGET_OPTIONS = [
    "Generelt",
    "Seng",
    "Rom",
    "Ventilasjon",
    "Lys",
    "Energi",
    "Parkering",
    "Renhold",
    "Utstyr",
    "Leverandør",
]

MAINTENANCE_ACTION_OPTIONS = [
    "Kontroll",
    "Vedlikehold",
    "Rengjøring",
    "Reparasjon",
    "Bytte",
    "Justering",
    "Påfyll",
    "Bestilling",
    "Observasjon",
]

MAINTENANCE_PRIORITY_OPTIONS = ["Normal", "Lav", "Høy", "Kritisk"]

ADMIN_TASK_SEVERITY_SORT = {
    "Kritisk": 0,
    "Høy": 1,
    "Medium": 2,
    "Lav": 3,
}

ENERGY_NODE_TYPES = {"zwave_device", "output", "child_device", "meter", "logical"}

ENERGY_LOAD_POWER_PROFILES = {"unknown", "fixed", "variable"}

EASYPARK_REQUIRED_COLUMNS = {
    "Parking area",
    "Source parking system",
    "Area number",
    "Parking ID",
    "Start date",
}

ROBOROCK_DOOR_AUTOMATION_POLL_SECONDS = 30
