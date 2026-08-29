from __future__ import annotations

import re
from pathlib import Path

from microapp_backend import DomainAppConfig, create_domain_app


APP_DIR = Path(__file__).resolve().parents[1]
MODULES = {"auth/me", "modules/koble"}
DOMAIN_PATTERN = re.compile(r"(?:actions/koble|koble)(?:/.*)?")

app = create_domain_app(
    DomainAppConfig(
        name="Lilletorget Koble",
        short_name="Koble",
        service="link_app",
        build_env="LINK_APP_BUILD",
        commit_env="LINK_APP_COMMIT",
        app_dir=APP_DIR,
        port=8158,
        allowed_paths={"GET": MODULES},
        allowed_patterns={method: (DOMAIN_PATTERN,) for method in ("GET", "POST", "PATCH", "PUT", "DELETE")},
    )
)
