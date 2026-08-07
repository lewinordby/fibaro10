from __future__ import annotations

from pathlib import Path

from microapp_backend import DomainAppConfig, create_domain_app


APP_DIR = Path(__file__).resolve().parents[1]

app = create_domain_app(
    DomainAppConfig(
        name="Lilletorget Omsetning",
        short_name="Omsetning",
        service="revenue_app",
        build_env="REVENUE_APP_BUILD",
        commit_env="REVENUE_APP_COMMIT",
        app_dir=APP_DIR,
        port=8151,
        pwa_description="Omsetning, utvikling og periodesammenligninger for Lilletorget.",
        pwa_theme_color="#e11d48",
        pwa_categories=("business", "finance", "productivity"),
        allowed_paths={
            "GET": {
                "auth/me",
                "overview",
                "modules/omsetning",
                "status/comparison",
                "omsetning/year-comparison",
                "revenue/month",
            }
        },
    )
)
