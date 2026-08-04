from __future__ import annotations

import re
from pathlib import Path

from microapp_backend import DomainAppConfig, create_domain_app


APP_DIR = Path(__file__).resolve().parents[1]
MODULES = {"auth/me", "overview", "modules/soling", "soling/year-comparison", "status/comparison"}
DOMAIN_PATTERN = re.compile(r"(?:actions/soling|soling|sun2|settlements)(?:/.*)?")
SESSION_IMAGE_PATTERN = re.compile(r"soling/enkeltimer/\d+/(?:bilde\.jpg|bilder/\d+\.jpg)")

app = create_domain_app(
    DomainAppConfig(
        name="Lilletorget Soling",
        short_name="Soling",
        service="sun_app",
        build_env="SUN_APP_BUILD",
        commit_env="SUN_APP_COMMIT",
        app_dir=APP_DIR,
        port=8153,
        allowed_paths={"GET": MODULES},
        allowed_patterns={method: (DOMAIN_PATTERN,) for method in ("GET", "POST", "PATCH", "PUT", "DELETE")},
        resource_patterns=(SESSION_IMAGE_PATTERN,),
    )
)
