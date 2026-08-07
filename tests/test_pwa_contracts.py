from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

from microapp_backend.pwa import (
    PWA_ICON_192_PATH,
    PWA_ICON_512_PATH,
    PWA_MASKABLE_ICON_PATH,
    PwaConfig,
    inject_pwa_head,
    register_pwa,
)


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def test_manifest_contains_complete_install_metadata() -> None:
    manifest = PwaConfig(
        name="Lilletorget Test",
        short_name="Test",
        description="Testapp for Lilletorget.",
        theme_color="#123456",
    ).manifest()

    assert manifest["id"] == "/"
    assert manifest["scope"] == "/"
    assert manifest["start_url"] == "/"
    assert manifest["display"] == "standalone"
    assert manifest["lang"] == "nb-NO"
    assert manifest["theme_color"] == "#123456"
    assert manifest["prefer_related_applications"] is False
    assert [(icon["sizes"], icon["purpose"]) for icon in manifest["icons"]] == [
        ("192x192", "any"),
        ("512x512", "any"),
        ("512x512", "maskable"),
    ]


def test_registered_manifest_and_icons_are_public_and_cacheable() -> None:
    app = FastAPI()
    register_pwa(
        app,
        PwaConfig(name="Lilletorget Test", short_name="Test", description="Test"),
    )

    with TestClient(app) as client:
        manifest = client.get("/manifest.webmanifest")
        icon = client.get("/pwa-icon-512.png")
        small_icon = client.get("/pwa-icon-192.png")
        maskable_icon = client.get("/pwa-icon-maskable-512.png")
        apple_icon = client.get("/apple-touch-icon.png")

    assert manifest.status_code == 200
    assert manifest.headers["content-type"].startswith("application/manifest+json")
    assert "max-age=3600" in manifest.headers["cache-control"]
    assert icon.status_code == 200
    assert icon.headers["content-type"].startswith("image/png")
    assert apple_icon.content == icon.content
    assert len(small_icon.content) == PWA_ICON_192_PATH.stat().st_size
    assert len(icon.content) == PWA_ICON_512_PATH.stat().st_size
    assert len(maskable_icon.content) == PWA_MASKABLE_ICON_PATH.stat().st_size


def test_pwa_head_is_injected_once() -> None:
    config = PwaConfig(name="Lilletorget Test", short_name="Test", description="Test")
    source = "<!doctype html><html><head><title>Test</title></head><body></body></html>"

    first = inject_pwa_head(source, config)
    second = inject_pwa_head(first, config)

    assert first == second
    assert first.count('rel="manifest"') == 1
    assert 'rel="apple-touch-icon"' in first
    assert 'name="apple-mobile-web-app-capable"' in first


def test_brand_icon_is_square_and_nonempty() -> None:
    assert Path(PWA_ICON_192_PATH).stat().st_size > 10_000
    assert Path(PWA_ICON_512_PATH).stat().st_size > 50_000
    assert Path(PWA_MASKABLE_ICON_PATH).stat().st_size > 30_000
    assert png_dimensions(PWA_ICON_192_PATH) == (192, 192)
    assert png_dimensions(PWA_ICON_512_PATH) == (512, 512)
    assert png_dimensions(PWA_MASKABLE_ICON_PATH) == (512, 512)


def test_pwa_import_does_not_load_domain_runtime_dependencies() -> None:
    check = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "from microapp_backend import PwaConfig, register_pwa; "
                "assert 'microapp_backend.runtime' not in sys.modules"
            ),
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
    )

    assert check.returncode == 0, check.stderr


def test_login_surfaces_advertise_pwa_before_authentication() -> None:
    root = Path(__file__).resolve().parents[1]
    sources = (
        (root / "templates" / "login.html").read_text(encoding="utf-8"),
        (root / "fibaro10ipad" / "app" / "main.py").read_text(encoding="utf-8"),
    )

    for source in sources:
        assert 'rel="manifest" href="/manifest.webmanifest"' in source
        assert 'name="apple-mobile-web-app-capable" content="yes"' in source
        assert 'rel="apple-touch-icon"' in source
