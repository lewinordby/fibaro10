from __future__ import annotations

import json
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response


PWA_ICON_192_PATH = Path(__file__).resolve().parent / "pwa-icon-192.png"
PWA_ICON_512_PATH = Path(__file__).resolve().parent / "pwa-icon-512.png"
PWA_MASKABLE_ICON_PATH = Path(__file__).resolve().parent / "pwa-icon-maskable-512.png"
PWA_ICON_PATH = PWA_ICON_512_PATH


@dataclass(frozen=True)
class PwaConfig:
    name: str
    short_name: str
    description: str
    theme_color: str = "#4f46e5"
    background_color: str = "#f8fafc"
    start_url: str = "/"
    scope: str = "/"
    app_id: str = "/"
    orientation: str = "any"
    categories: tuple[str, ...] = field(default_factory=lambda: ("business", "productivity"))
    shortcuts: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    scope_extensions: tuple[str, ...] = field(default_factory=tuple)

    def manifest(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.app_id,
            "name": self.name,
            "short_name": self.short_name,
            "description": self.description,
            "lang": "nb-NO",
            "dir": "ltr",
            "start_url": self.start_url,
            "scope": self.scope,
            "display": "standalone",
            "display_override": ["standalone", "minimal-ui"],
            "orientation": self.orientation,
            "background_color": self.background_color,
            "theme_color": self.theme_color,
            "categories": list(self.categories),
            "prefer_related_applications": False,
            "icons": [
                {
                    "src": "/pwa-icon-192.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any",
                },
                {
                    "src": "/pwa-icon-512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any",
                },
                {
                    "src": "/pwa-icon-maskable-512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "maskable",
                },
            ],
            "launch_handler": {"client_mode": "navigate-existing"},
        }
        if self.shortcuts:
            payload["shortcuts"] = list(self.shortcuts)
        if self.scope_extensions:
            payload["scope_extensions"] = [
                {"type": "origin", "origin": origin}
                for origin in dict.fromkeys(self.scope_extensions)
            ]
        return payload


def pwa_head_tags(config: PwaConfig) -> str:
    return (
        f'<meta name="theme-color" content="{escape(config.theme_color)}">'
        f'<meta name="application-name" content="{escape(config.short_name)}">'
        '<meta name="mobile-web-app-capable" content="yes">'
        '<meta name="apple-mobile-web-app-capable" content="yes">'
        '<meta name="apple-mobile-web-app-status-bar-style" content="default">'
        f'<meta name="apple-mobile-web-app-title" content="{escape(config.short_name)}">'
        '<link rel="manifest" href="/manifest.webmanifest">'
        '<link rel="icon" href="/pwa-icon-192.png" type="image/png">'
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">'
    )


def inject_pwa_head(html: str, config: PwaConfig) -> str:
    if 'rel="manifest"' in html or "rel='manifest'" in html:
        return html
    marker = "</head>"
    if marker not in html:
        return html
    return html.replace(marker, f"{pwa_head_tags(config)}{marker}", 1)


def register_pwa(app: FastAPI, config: PwaConfig) -> None:
    @app.get("/manifest.webmanifest", include_in_schema=False)
    async def pwa_manifest() -> Response:
        return Response(
            content=json.dumps(config.manifest(), ensure_ascii=False, separators=(",", ":")),
            media_type="application/manifest+json",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    def icon_response(icon_path: Path) -> FileResponse:
        return FileResponse(
            icon_path,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )

    async def icon_192() -> FileResponse:
        return icon_response(PWA_ICON_192_PATH)

    async def icon_512() -> FileResponse:
        return icon_response(PWA_ICON_512_PATH)

    async def icon_maskable() -> FileResponse:
        return icon_response(PWA_MASKABLE_ICON_PATH)

    app.add_api_route("/pwa-icon-192.png", icon_192, methods=["GET"], include_in_schema=False)
    app.add_api_route("/pwa-icon-512.png", icon_512, methods=["GET"], include_in_schema=False)
    app.add_api_route("/pwa-icon-maskable-512.png", icon_maskable, methods=["GET"], include_in_schema=False)
    app.add_api_route("/apple-touch-icon.png", icon_512, methods=["GET"], include_in_schema=False)
