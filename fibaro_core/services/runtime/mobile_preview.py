"""Mobile Preview services with explicit process dependencies."""

from dataclasses import dataclass
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import HTMLResponse
from types import SimpleNamespace
from typing import Any
from typing import Any, Callable
from typing import Dict
from typing import List
from urllib.parse import quote


@dataclass
class Dependencies:
    MOBILE_PREVIEW_MONEY_KEYS: Any
    MOBILE_PREVIEW_REFRESH_SECONDS: Any
    MOBILE_PREVIEW_SCREENS: Any
    mobile_preview_access_key: Callable[..., Any]


def create_service(dependencies: Dependencies):

    def mobile_preview_screen_payload(screen: Dict[str, Any]) -> Dict[str, Any]:
        key = str(screen["key"])
        return {
            "key": key,
            "title": screen["title"],
            "subtitle": screen["subtitle"],
            "sourcePath": screen["source_path"],
            "frameUrl": f"/api/mobile-preview/frame/{quote(key, safe='')}",
        }

    def mobile_preview_can_view_money(request: Request) -> bool:
        return bool(
            getattr(request.state, "auth_is_master", False)
            or getattr(request.state, "auth_can_settings", False)
        )

    def mobile_preview_screens_for_request(request: Request) -> List[Dict[str, Any]]:
        MOBILE_PREVIEW_MONEY_KEYS = dependencies.MOBILE_PREVIEW_MONEY_KEYS
        MOBILE_PREVIEW_SCREENS = dependencies.MOBILE_PREVIEW_SCREENS
        if mobile_preview_can_view_money(request):
            return MOBILE_PREVIEW_SCREENS
        return [
            screen
            for screen in MOBILE_PREVIEW_SCREENS
            if str(screen.get("key") or "") not in MOBILE_PREVIEW_MONEY_KEYS
        ]

    def mobile_preview_injected_head() -> str:
        MOBILE_PREVIEW_REFRESH_SECONDS = dependencies.MOBILE_PREVIEW_REFRESH_SECONDS
        return f"""
  <style>
    html,
    body {{
      min-width: 0 !important;
      overflow: hidden !important;
      background: #f6f8fb !important;
    }}
    body {{
      margin: 0 !important;
    }}
    .topbar,
    .detail-hero {{
      display: none !important;
    }}
    .dashboard {{
      padding: 8px 10px 10px !important;
      gap: 10px !important;
    }}
    a,
    button,
    input,
    select,
    textarea,
    form {{
      pointer-events: none !important;
    }}
    .metric-card,
    .pulse-card,
    .temperature-card,
    .section-block,
    .detail-card,
    .detail-stat {{
      box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06) !important;
    }}
  </style>
  <script>
    window.setTimeout(() => window.location.reload(), {MOBILE_PREVIEW_REFRESH_SECONDS * 1000});
  </script>
"""

    def mobile_preview_html(html: str) -> str:
        injected = mobile_preview_injected_head()
        if "</head>" in html:
            html = html.replace("</head>", f"{injected}</head>", 1)
        else:
            html = f"{injected}{html}"
        return html

    async def render_mobile_preview_screen(request: Request, screen_key: str) -> HTMLResponse:
        MOBILE_PREVIEW_MONEY_KEYS = dependencies.MOBILE_PREVIEW_MONEY_KEYS
        MOBILE_PREVIEW_SCREENS = dependencies.MOBILE_PREVIEW_SCREENS
        mobile_preview_access_key = dependencies.mobile_preview_access_key
        screen = next((item for item in MOBILE_PREVIEW_SCREENS if item["key"] == screen_key), None)
        if not screen:
            raise HTTPException(status_code=404, detail="Ukjent mobilskjerm")
        if screen_key in MOBILE_PREVIEW_MONEY_KEYS and not mobile_preview_can_view_money(request):
            raise HTTPException(status_code=403, detail="Mobilskjermen krever tilgang til omsetning")

        from online_dashboard.app import main as mobile_app

        fake_request = SimpleNamespace(state=SimpleNamespace(access_key=mobile_preview_access_key(request)))
        handlers = {
            "home": mobile_app.dashboard,
            "soling": mobile_app.soling_detail,
            "parkering": mobile_app.parking_detail,
            "omsetning": mobile_app.revenue_detail,
            "omsetning-uke": mobile_app.revenue_week_detail,
            "energi": mobile_app.energy_detail,
            "temperatur": mobile_app.temperature_detail,
            "lys": mobile_app.light_detail,
            "ventilasjon": mobile_app.ventilation_detail,
        }
        response = await handlers[screen_key](fake_request)
        if not isinstance(response, HTMLResponse):
            raise HTTPException(status_code=403, detail="Mobilskjermen kan ikke vises for denne brukeren")
        html = response.body.decode(response.charset or "utf-8", errors="replace")
        return HTMLResponse(
            mobile_preview_html(html),
            headers={"Cache-Control": "no-store"},
        )

    return {
        "mobile_preview_can_view_money": mobile_preview_can_view_money,
        "mobile_preview_html": mobile_preview_html,
        "mobile_preview_injected_head": mobile_preview_injected_head,
        "mobile_preview_screen_payload": mobile_preview_screen_payload,
        "mobile_preview_screens_for_request": mobile_preview_screens_for_request,
        "render_mobile_preview_screen": render_mobile_preview_screen,
    }
