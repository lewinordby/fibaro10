from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import httpx
from fastapi import Request

from microapp_backend import DomainAppConfig, create_domain_app


APP_DIR = Path(__file__).resolve().parents[1]


async def lookup_worklist(request: Request, client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    mode = "omrade" if request.url.path.casefold().endswith("mangler-omrade") else "navn"
    params = dict(request.query_params)
    params["include_not_found"] = "true"
    response = await client.get(
        f"/api/parkering/kjoretoy/mangler-{mode}",
        params=params,
        headers=headers,
    )
    response.raise_for_status()
    return response.json()

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
                "cars/parking-control-report",
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
                re.compile(r"cars/day/[a-z0-9-]+/detections"),
                re.compile(r"parkering/kjoretoy/mangler-(?:navn|omrade)"),
                re.compile(r"settlements/\d+"),
                re.compile(r"settlements/\d+/attachment"),
                re.compile(r"unifi-protect/recognitions/\d+/snapshot"),
            ),
            "POST": (re.compile(r"parking/vehicles/[a-z0-9-]+/clear-not-found"),),
        },
        adapters={
            "parkering/kjoretoy/mangler-navn": lookup_worklist,
            "parkering/kjoretoy/mangler-omrade": lookup_worklist,
        },
    )
)
