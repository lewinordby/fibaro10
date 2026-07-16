import asyncio
import os
import unittest
from datetime import datetime
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

from main import (  # noqa: E402
    EnergyCircuit,
    EnergyLoad,
    EnergyNode,
    build_energy_circuit_loads_payload,
    clean_energy_node_values,
    clean_energy_load_values,
    energy_node_branch_ids,
    energy_node_from_values,
    hc3_energy_device_summary,
    hc3_energy_nodes_live,
    validate_energy_load_power_values,
    validate_energy_node_hc3_values,
    validate_energy_node_profile_values,
)


class EnergyTopologyTests(unittest.TestCase):
    def test_nested_node_inherits_measurement_coverage(self):
        circuit = EnergyCircuit(circuit_no=6, description="Loft", breaker_rating_a=16, is_sunbed=False)
        meter = EnergyNode(
            id=1,
            name="Kursmåler",
            circuit_no=6,
            node_type="zwave_device",
            hc3_power_device_id=530,
            has_meter=True,
            active=True,
        )
        output = EnergyNode(
            id=2,
            name="Utgang 1",
            circuit_no=6,
            parent_node_id=1,
            node_type="output",
            hc3_switch_device_id=511,
            has_switch=True,
            active=True,
        )
        measured_load = EnergyLoad(
            id=1,
            name="Vifte VIP",
            circuit_no=6,
            energy_node_id=2,
            power_profile="variable",
            min_power_w=180,
            expected_power_w=320,
            max_power_w=360,
            active=True,
        )
        direct_load = EnergyLoad(
            id=2,
            name="Bredbåndsruter",
            circuit_no=6,
            expected_power_w=18,
            active=True,
        )

        payload = build_energy_circuit_loads_payload([circuit], [measured_load, direct_load], [meter, output])
        row = payload["circuits"][0]

        self.assertEqual(row["nodeCount"], 2)
        self.assertEqual(row["nodes"][0]["children"][0]["loads"][0]["name"], "Vifte VIP")
        self.assertEqual(row["nodes"][0]["children"][0]["loads"][0]["powerProfile"], "variable")
        self.assertEqual(row["nodes"][0]["children"][0]["loads"][0]["minPowerW"], 180)
        self.assertEqual(row["nodes"][0]["children"][0]["loads"][0]["maxPowerW"], 360)
        self.assertEqual(row["directLoads"][0]["name"], "Bredbåndsruter")
        self.assertEqual(row["measuredLoadCount"], 1)
        self.assertEqual(row["unmeasuredLoadCount"], 1)

    def test_hc3_power_meter_value_is_read_from_value_property(self):
        summary = hc3_energy_device_summary(
            {
                "id": 530,
                "name": "126.0 Kurs 6",
                "type": "com.fibaro.powerMeter",
                "properties": {"value": 742.5, "dead": False, "enabled": True},
            }
        )

        self.assertEqual(summary["powerW"], 742.5)
        self.assertTrue(summary["hasPower"])
        self.assertFalse(summary["dead"])

    def test_binary_switch_exposes_power_and_switch_state(self):
        summary = hc3_energy_device_summary(
            {
                "id": 449,
                "name": "Avfukter kjeller",
                "type": "com.fibaro.binarySwitch",
                "properties": {"value": True, "power": 161.9, "energy": 102.9},
            }
        )

        self.assertEqual(summary["powerW"], 161.9)
        self.assertTrue(summary["switchState"])
        self.assertTrue(summary["hasSwitch"])

    def test_variable_power_profile_rejects_reversed_range(self):
        values = clean_energy_load_values(
            {
                "power_profile": "variable",
                "min_power_w": 900,
                "expected_power_w": 600,
                "max_power_w": 500,
            }
        )

        with self.assertRaisesRegex(Exception, "Minimum effekt"):
            validate_energy_load_power_values(values)

    def test_existing_expected_power_defaults_to_fixed_profile(self):
        values = validate_energy_load_power_values({"expected_power_w": 1200})

        self.assertEqual(values["power_profile"], "fixed")

    def test_profile_change_clears_fields_that_no_longer_apply(self):
        existing = EnergyLoad(
            power_profile="variable",
            min_power_w=200,
            expected_power_w=350,
            max_power_w=500,
        )

        unknown = validate_energy_load_power_values({"power_profile": "unknown"}, existing=existing)
        fixed = validate_energy_load_power_values(
            {"power_profile": "fixed", "expected_power_w": 400},
            existing=existing,
        )

        self.assertIsNone(unknown["expected_power_w"])
        self.assertIsNone(unknown["min_power_w"])
        self.assertIsNone(unknown["max_power_w"])
        self.assertEqual(fixed["expected_power_w"], 400)
        self.assertIsNone(fixed["min_power_w"])
        self.assertIsNone(fixed["max_power_w"])

    def test_expected_power_promotes_unknown_existing_profile_to_fixed(self):
        existing = EnergyLoad(power_profile="unknown")

        values = validate_energy_load_power_values({"expected_power_w": 275}, existing=existing)

        self.assertEqual(values["power_profile"], "fixed")

    def test_energy_node_factory_preserves_endpoint_and_uses_standard_type(self):
        node = energy_node_from_values(
            {
                "circuit_no": 6,
                "endpoint_key": "Q1",
                "hc3_switch_device_id": 511,
            },
            "Vifte VIP",
            datetime(2026, 7, 16, 14, 0),
        )

        self.assertEqual(node.endpoint_key, "Q1")
        self.assertEqual(node.node_type, "zwave_device")
        self.assertTrue(node.has_switch)

    def test_energy_node_type_is_normalized_and_validated(self):
        self.assertEqual(clean_energy_node_values({"node_type": "zwave_point"})["node_type"], "zwave_device")
        with self.assertRaisesRegex(Exception, "Ugyldig type"):
            clean_energy_node_values({"node_type": "tilfeldig"})

    def test_energy_node_profiles_require_relevant_parameters(self):
        with self.assertRaisesRegex(Exception, "overordnet enhet"):
            validate_energy_node_profile_values({"node_type": "output", "endpoint_key": "Q1"})
        with self.assertRaisesRegex(Exception, "kanal eller utgangsnummer"):
            validate_energy_node_profile_values({"node_type": "output", "parent_node_id": 4})
        with self.assertRaisesRegex(Exception, "rapporterer watt"):
            validate_energy_node_profile_values({"node_type": "meter"})

        validate_energy_node_profile_values({
            "node_type": "output",
            "parent_node_id": 4,
            "endpoint_key": "Q1",
        })
        validate_energy_node_profile_values({"node_type": "meter", "hc3_power_device_id": 530})

    def test_energy_node_branch_contains_all_descendants_only(self):
        nodes = [
            EnergyNode(id=1, name="Rot"),
            EnergyNode(id=2, name="Utgang", parent_node_id=1),
            EnergyNode(id=3, name="Underenhet", parent_node_id=2),
            EnergyNode(id=4, name="Annen rot"),
        ]

        self.assertEqual(energy_node_branch_ids(nodes, 1), {1, 2, 3})

    def test_hc3_link_validation_rejects_energy_counter_as_live_power(self):
        device = {
            "id": 398,
            "name": "Varmtvann energi",
            "type": "com.fibaro.energyMeter",
            "properties": {"value": 391.7, "dead": False, "enabled": True},
        }

        with (
            patch("main.hc3_api_is_configured", return_value=True),
            patch("main.hc3_cached_device_request", return_value=device),
            self.assertRaisesRegex(Exception, "ikke rapporterer watt"),
        ):
            asyncio.run(validate_energy_node_hc3_values({"hc3_power_device_id": 398}))

    def test_hc3_link_validation_requires_id_for_meter_flag(self):
        with self.assertRaisesRegex(Exception, "må kobles til"):
            asyncio.run(validate_energy_node_hc3_values({"has_meter": True}))

    def test_live_status_rejects_accumulated_energy_as_power(self):
        node = EnergyNode(
            id=9,
            name="Varmtvann",
            hc3_power_device_id=398,
            has_meter=True,
            active=True,
        )
        device = {
            "id": 398,
            "name": "Akkumulert energi",
            "type": "com.fibaro.energyMeter",
            "properties": {"value": 391.7, "dead": False, "enabled": True},
        }

        with (
            patch("main.hc3_api_is_configured", return_value=True),
            patch("main.hc3_cached_device_request", return_value=device),
        ):
            payload = asyncio.run(hc3_energy_nodes_live([node]))

        self.assertEqual(payload["nodes"]["9"]["status"], "error")
        self.assertIn("rapporterer ikke watt", payload["nodes"]["9"]["error"])


if __name__ == "__main__":
    unittest.main()
