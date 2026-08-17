#!/usr/bin/env python3
"""Create the private Fibaro10 A records in public Domeneshop DNS."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request


API_BASE = "https://api.domeneshop.no/v0"
DOMAIN = "lilletorget.net"
PRIVATE_IP = "192.168.20.219"
HOSTS = (
    "fibaro10",
    "app",
    "ny",
    "omsetning",
    "parkering",
    "soling",
    "energi",
    "drift",
    "vedlikehold",
    "system",
    "koble",
)


class DomeneshopClient:
    def __init__(self, token: str, secret: str) -> None:
        credentials = base64.b64encode(f"{token}:{secret}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {credentials}",
            "Accept": "application/json",
            "User-Agent": "fibaro10-dns-setup/1.0",
        }

    def request(self, method: str, path: str, payload: dict | None = None):
        data = json.dumps(payload).encode() if payload is not None else None
        headers = dict(self.headers)
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{API_BASE}{path}", data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")
            raise RuntimeError(f"Domeneshop svarte {error.code}: {detail}") from error
        return json.loads(body) if body else None


def configure(*, apply: bool) -> list[str]:
    token = os.environ.get("DOMENESHOP_API_TOKEN", "").strip()
    secret = os.environ.get("DOMENESHOP_API_SECRET", "").strip()
    if not token or not secret:
        raise RuntimeError(
            "DOMENESHOP_API_TOKEN og DOMENESHOP_API_SECRET må være satt"
        )

    client = DomeneshopClient(token, secret)
    domains = client.request("GET", f"/domains?domain={DOMAIN}")
    domain = next((item for item in domains if item.get("domain") == DOMAIN), None)
    if not domain:
        raise RuntimeError(f"Fant ikke {DOMAIN} i Domeneshop-kontoen")

    domain_id = domain["id"]
    records = client.request("GET", f"/domains/{domain_id}/dns")
    actions: list[str] = []

    for host in HOSTS:
        matching = [record for record in records if record.get("host") == host]
        conflicting = [
            record
            for record in matching
            if record.get("type") in {"CNAME", "ANAME"}
        ]
        if conflicting:
            types = ", ".join(sorted({record["type"] for record in conflicting}))
            raise RuntimeError(f"{host}.{DOMAIN} har allerede konfliktende {types}-post")

        a_records = [record for record in matching if record.get("type") == "A"]
        wanted = {"host": host, "ttl": 300, "type": "A", "data": PRIVATE_IP}
        correct = next(
            (record for record in a_records if record.get("data") == PRIVATE_IP), None
        )

        if correct:
            actions.append(f"OK       {host}.{DOMAIN} -> {PRIVATE_IP}")
            extras = [record for record in a_records if record["id"] != correct["id"]]
        elif a_records:
            current = a_records[0]
            actions.append(
                f"OPPDATER  {host}.{DOMAIN}: {current.get('data')} -> {PRIVATE_IP}"
            )
            if apply:
                client.request(
                    "PUT", f"/domains/{domain_id}/dns/{current['id']}", wanted
                )
            extras = a_records[1:]
        else:
            actions.append(f"OPPRETT  {host}.{DOMAIN} -> {PRIVATE_IP}")
            if apply:
                client.request("POST", f"/domains/{domain_id}/dns", wanted)
            extras = []

        for extra in extras:
            actions.append(
                f"FJERN    duplikat {host}.{DOMAIN} -> {extra.get('data')}"
            )
            if apply:
                client.request(
                    "DELETE", f"/domains/{domain_id}/dns/{extra['id']}"
                )

    return actions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply", action="store_true", help="Utfør endringene; standard er prøvekjøring"
    )
    args = parser.parse_args()
    try:
        for line in configure(apply=args.apply):
            print(line)
    except RuntimeError as error:
        print(f"FEIL: {error}", file=sys.stderr)
        return 1
    if not args.apply:
        print("Prøvekjøring. Bruk --apply for å utføre endringene.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
