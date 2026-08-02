"""Read-only connectivity probe for the local UniFi Protect integration API."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import socket
import ssl
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_ENV_PATH = Path(__file__).resolve().parents[1] / ".env.unifi.local"
CAMERAS_PATH = "/proxy/protect/integration/v1/cameras"
EVENTS_PATH = "/proxy/protect/integration/v1/subscribe/events"


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def ssl_context(verify: bool) -> ssl.SSLContext:
    return ssl.create_default_context() if verify else ssl._create_unverified_context()


def get_cameras(base_url: str, api_key: str, verify: bool) -> list[dict]:
    request = Request(
        f"{base_url.rstrip('/')}{CAMERAS_PATH}",
        headers={"Accept": "application/json", "X-API-Key": api_key},
    )
    try:
        with urlopen(request, timeout=15, context=ssl_context(verify)) as response:
            payload = json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"Protect camera API returned HTTP {error.code}") from error
    if not isinstance(payload, list):
        raise RuntimeError("Protect camera API did not return a JSON array")
    return [camera for camera in payload if isinstance(camera, dict)]


def websocket_handshake(base_url: str, api_key: str, verify: bool) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("UNIFI_PROTECT_NVR_URL must be an http(s) URL")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    connection: socket.socket = socket.create_connection((parsed.hostname, port), timeout=15)
    try:
        if parsed.scheme == "https":
            connection = ssl_context(verify).wrap_socket(connection, server_hostname=parsed.hostname)
        nonce = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {EVENTS_PATH} HTTP/1.1\r\n"
            f"Host: {parsed.netloc}\r\n"
            "Accept: application/json\r\n"
            "Connection: Upgrade\r\n"
            "Upgrade: websocket\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            f"Sec-WebSocket-Key: {nonce}\r\n"
            f"X-API-Key: {api_key}\r\n"
            "\r\n"
        )
        connection.sendall(request.encode("ascii"))
        response = bytearray()
        while b"\r\n\r\n" not in response and len(response) < 65536:
            chunk = connection.recv(4096)
            if not chunk:
                break
            response.extend(chunk)
        status_line = bytes(response).split(b"\r\n", 1)[0].decode("ascii", errors="replace")
        if " 101 " not in status_line:
            raise RuntimeError(f"Protect WebSocket handshake failed: {status_line}")
        return status_line
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_PATH)
    args = parser.parse_args()

    config = read_env_file(args.env_file)
    base_url = config.get("UNIFI_PROTECT_NVR_URL", "").strip()
    api_key = config.get("UNIFI_PROTECT_API_KEY", "").strip()
    verify = config.get("UNIFI_PROTECT_VERIFY_SSL", "false").lower() in {"1", "true", "yes", "on"}
    if not base_url or not api_key:
        raise SystemExit("UNIFI_PROTECT_NVR_URL or UNIFI_PROTECT_API_KEY is missing")

    cameras = get_cameras(base_url, api_key, verify)
    print(f"REST API: OK ({len(cameras)} cameras)")
    for camera in cameras:
        print(f"- {camera.get('name') or camera.get('id')} [{camera.get('state') or 'unknown'}]")
    print(f"WebSocket: OK ({websocket_handshake(base_url, api_key, verify)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
