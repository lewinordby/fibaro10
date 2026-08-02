from __future__ import annotations

import re
from pathlib import Path

from microapp_backend import DomainAppConfig, create_domain_app


APP_DIR = Path(__file__).resolve().parents[1]
DOMAIN_PATTERN = re.compile(r"(?:actions/energi|energy|energi|elvia|hc3/energy)(?:/.*)?")

app = create_domain_app(
    DomainAppConfig(
        name="Lilletorget Energi",
        short_name="Energi",
        service="energy_app",
        build_env="ENERGY_APP_BUILD",
        commit_env="ENERGY_APP_COMMIT",
        app_dir=APP_DIR,
        port=8154,
        allowed_paths={"GET": {"auth/me", "modules/energi"}},
        allowed_patterns={method: (DOMAIN_PATTERN,) for method in ("GET", "POST", "PATCH", "PUT", "DELETE")},
    )
)
