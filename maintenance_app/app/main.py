from __future__ import annotations

import re
from pathlib import Path

from microapp_backend import DomainAppConfig, create_domain_app


APP_DIR = Path(__file__).resolve().parents[1]
DOMAIN_PATTERN = re.compile(r"(?:actions/vedlikehold|maintenance)(?:/.*)?")

app = create_domain_app(
    DomainAppConfig(
        name="Lilletorget Vedlikehold",
        short_name="Vedlikehold",
        service="maintenance_app",
        build_env="MAINTENANCE_APP_BUILD",
        commit_env="MAINTENANCE_APP_COMMIT",
        app_dir=APP_DIR,
        port=8156,
        allowed_paths={"GET": {"auth/me", "modules/vedlikehold"}},
        allowed_patterns={method: (DOMAIN_PATTERN,) for method in ("GET", "POST", "PATCH", "PUT", "DELETE")},
    )
)
