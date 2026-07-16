import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

from main import (  # noqa: E402
    EnergyCircuit,
    EnergyLoad,
    EnergyNode,
    build_energy_circuit_loads_payload,
    hc3_energy_device_summary,
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
            expected_power_w=320,
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


if __name__ == "__main__":
    unittest.main()
