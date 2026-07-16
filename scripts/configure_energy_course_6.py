from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from main import (  # noqa: E402
    EnergyCircuit,
    EnergyLoad,
    EnergyNode,
    async_session,
    validate_energy_node_hc3_values,
    validate_energy_node_link_uniqueness,
)


CIRCUIT_NO = 6


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def upsert_node(
    session,
    *,
    name: str,
    hc3_device_id: int,
    parent_node_id: int | None,
    values: dict[str, Any],
) -> EnergyNode:
    matches = (
        await session.execute(select(EnergyNode).where(EnergyNode.hc3_device_id == hc3_device_id))
    ).scalars().all()
    if len(matches) > 1:
        raise RuntimeError(f"Flere energipunkter bruker HC3-enhet {hc3_device_id}.")
    node = matches[0] if matches else None
    if node is not None and node.circuit_no not in (None, CIRCUIT_NO):
        raise RuntimeError(f"HC3-enhet {hc3_device_id} er allerede koblet til kurs {node.circuit_no}.")
    is_new = node is None
    if is_new:
        node = EnergyNode(created_at=utc_now(), source="course-6-setup")

    hc3_values = {
        "hc3_device_id": hc3_device_id,
        "hc3_power_device_id": values.get("hc3_power_device_id"),
        "hc3_switch_device_id": values.get("hc3_switch_device_id"),
        "has_meter": values.get("has_meter", False),
        "has_switch": values.get("has_switch", False),
    }
    await validate_energy_node_hc3_values(hc3_values)
    await validate_energy_node_link_uniqueness(
        session,
        hc3_values["hc3_power_device_id"],
        hc3_values["hc3_switch_device_id"],
        node_id=node.id,
    )

    node.name = name
    node.circuit_no = CIRCUIT_NO
    node.parent_node_id = parent_node_id
    node.hc3_device_id = hc3_device_id
    for key, value in values.items():
        setattr(node, key, value)
    node.active = True
    node.updated_at = utc_now()
    if is_new:
        session.add(node)
    await session.flush()
    return node


async def upsert_load(
    session,
    *,
    name: str,
    energy_node_id: int,
    load_type: str,
    area: str,
    controllable: bool,
    critical: bool,
    note: str,
) -> EnergyLoad:
    matches = (
        await session.execute(
            select(EnergyLoad)
            .where(EnergyLoad.circuit_no == CIRCUIT_NO)
            .where(EnergyLoad.name == name)
        )
    ).scalars().all()
    if len(matches) > 1:
        raise RuntimeError(f"Flere laster på kurs {CIRCUIT_NO} heter {name}.")
    load = matches[0] if matches else None
    if load is None:
        load = EnergyLoad(created_at=utc_now(), source="course-6-setup")
        session.add(load)

    load.name = name
    load.load_type = load_type
    load.area = area
    load.circuit_no = CIRCUIT_NO
    load.energy_node_id = energy_node_id
    load.power_profile = "unknown"
    load.expected_power_w = None
    load.min_power_w = None
    load.max_power_w = None
    load.measured_direct = False
    load.fibaro_device_id = None
    load.fibaro_meter_id = None
    load.zwave_switch_id = None
    load.controllable = controllable
    load.critical = critical
    load.active = True
    load.note = note
    load.updated_at = utc_now()
    await session.flush()
    return load


async def configure(*, apply: bool) -> dict[str, Any]:
    async with async_session() as session:
        circuit = (
            await session.execute(select(EnergyCircuit).where(EnergyCircuit.circuit_no == CIRCUIT_NO))
        ).scalars().first()
        if circuit is None:
            raise RuntimeError(f"Kurs {CIRCUIT_NO} finnes ikke i energy_circuits.")

        meter = await upsert_node(
            session,
            name="Kurs 6 · strømmåler",
            hc3_device_id=527,
            parent_node_id=None,
            values={
                "node_type": "meter",
                "manufacturer": None,
                "model": "QMEM-0A1PC16EU",
                "device_type": "Z-Wave kursmåler",
                "hc3_power_device_id": 530,
                "hc3_switch_device_id": None,
                "endpoint_key": "126.0",
                "has_meter": True,
                "has_switch": False,
                "area": "VIP-loft",
                "note": "Måler samlet realtime-effekt. Akkumulert HC3-måler er 529.",
            },
        )
        relay = await upsert_node(
            session,
            name="Nexa 2-kanals bryter",
            hc3_device_id=509,
            parent_node_id=meter.id,
            values={
                "node_type": "child_device",
                "manufacturer": "Nexa / Everspring",
                "model": "AN196-0",
                "device_type": "2-kanals Z-Wave-relé",
                "hc3_power_device_id": None,
                "hc3_switch_device_id": None,
                "endpoint_key": "123.0",
                "has_meter": False,
                "has_switch": False,
                "area": "VIP-loft",
                "note": "Fysisk tokomponents relé uten egen effektmåling. Utgangene ligger under enheten.",
            },
        )
        fan_output = await upsert_node(
            session,
            name="Utgang 1 · Innluft VIP",
            hc3_device_id=511,
            parent_node_id=relay.id,
            values={
                "node_type": "output",
                "manufacturer": None,
                "model": None,
                "device_type": "Reléutgang",
                "hc3_power_device_id": None,
                "hc3_switch_device_id": 511,
                "endpoint_key": "123.1",
                "has_meter": False,
                "has_switch": True,
                "area": "VIP",
                "note": "Styrer innluftsviften i VIP. Effekt inngår i Kurs 6-måleren.",
            },
        )
        light_output = await upsert_node(
            session,
            name="Utgang 2 · Lys loft massasje",
            hc3_device_id=512,
            parent_node_id=relay.id,
            values={
                "node_type": "output",
                "manufacturer": None,
                "model": None,
                "device_type": "Reléutgang",
                "hc3_power_device_id": None,
                "hc3_switch_device_id": 512,
                "endpoint_key": "123.2",
                "has_meter": False,
                "has_switch": True,
                "area": "Loft massasje",
                "note": "Styrer loftlyset ved massasje. Effekt inngår i Kurs 6-måleren.",
            },
        )

        loads = [
            await upsert_load(
                session,
                name="Innluftsvifte VIP",
                energy_node_id=fan_output.id,
                load_type="Ventilasjon",
                area="VIP",
                controllable=True,
                critical=False,
                note="Styrt av Nexa kanal 123.1 / HC3 511.",
            ),
            await upsert_load(
                session,
                name="Lys loft massasje",
                energy_node_id=light_output.id,
                load_type="Belysning",
                area="Loft massasje",
                controllable=True,
                critical=False,
                note="Styrt av Nexa kanal 123.2 / HC3 512.",
            ),
            await upsert_load(
                session,
                name="Bredbåndsruter",
                energy_node_id=meter.id,
                load_type="Elektronikk",
                area="VIP-loft",
                controllable=False,
                critical=True,
                note="Koblet direkte etter Kurs 6-måleren og ikke via Nexa-reléet.",
            ),
        ]

        result = {
            "mode": "apply" if apply else "dry-run",
            "circuit": CIRCUIT_NO,
            "nodes": [
                {"id": node.id, "name": node.name, "parentNodeId": node.parent_node_id}
                for node in (meter, relay, fan_output, light_output)
            ],
            "loads": [
                {"id": load.id, "name": load.name, "energyNodeId": load.energy_node_id}
                for load in loads
            ],
        }
        if apply:
            await session.commit()
        else:
            await session.rollback()
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Konfigurer energitopologien for kurs 6.")
    parser.add_argument("--apply", action="store_true", help="Lagre endringene. Uten flagget kjøres en dry-run.")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(configure(apply=args.apply)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
