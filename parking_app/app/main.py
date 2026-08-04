from __future__ import annotations

import re
from pathlib import Path

from microapp_backend import DomainAppConfig, create_domain_app


APP_DIR = Path(__file__).resolve().parents[1]

app = create_domain_app(
    DomainAppConfig(
        name="Lilletorget Parkering",
        short_name="Parkering",
        service="parking_app",
        build_env="PARKING_APP_BUILD",
        commit_env="PARKING_APP_COMMIT",
        app_dir=APP_DIR,
        port=8152,
        allowed_paths={
            "GET": {
                "auth/me",
                "overview",
                "modules/parkering",
                "parkering/year-comparison",
                "status/comparison",
                "parkering/time-distribution",
                "parkering/weekly-averages",
                "parkering/weekly-averages/years",
                "cars/day",
            },
            "POST": {
                "actions/parkering/fetch-settlements",
                "actions/parkering/save-forecast",
                "actions/parkering/refresh",
                "actions/parkering/svv-sync",
                "actions/parkering/car-info-sync",
                "actions/parkering/clear-area-not-found",
            },
        },
        allowed_patterns={
            "GET": (
                re.compile(r"parking/vehicles/[a-z0-9-]+"),
                re.compile(r"settlements/\d+"),
                re.compile(r"settlements/\d+/attachment"),
                re.compile(r"unifi-protect/recognitions/\d+/snapshot"),
            ),
            "POST": (re.compile(r"parking/vehicles/[a-z0-9-]+/clear-not-found"),),
        },
    )
)
