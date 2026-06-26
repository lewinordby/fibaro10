from datetime import datetime
import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

import main


class ParkingRowApiTests(unittest.TestCase):
    def test_parking_row_api_includes_vehicle_details(self):
        row = main.ParkingSession(
            id=1,
            start_time=datetime(2026, 6, 26, 12, 0),
            car_license_number="AB12345",
            status="completed",
        )
        vehicle = main.ParkingVehicle(plate="AB12345", navn="Test Eier")
        details = main.ParkingVehicleDetails(
            plate="AB12345",
            merke="Toyota",
            typebetegnelse="Corolla",
            farge="Svart",
        )

        payload = main.parking_row_api(row, vehicle, details)

        self.assertEqual(payload["vehicle_owner"], "Test Eier")
        self.assertEqual(payload["vehicle_make"], "Toyota")
        self.assertEqual(payload["vehicle_type"], "Corolla")
        self.assertEqual(payload["vehicle_color"], "Svart")

    def test_parking_row_api_uses_foreign_lookup_fallback(self):
        row = main.ParkingSession(
            id=2,
            start_time=datetime(2026, 6, 26, 12, 0),
            car_license_number="HWN31L",
            status="completed",
        )
        vehicle = main.ParkingVehicle(
            plate="HWN31L",
            navn="",
            car_info_data={
                "fields": {
                    "brand": "Volvo",
                    "model": "XC60",
                    "color": "Gra",
                }
            },
        )

        payload = main.parking_row_api(row, vehicle)

        self.assertEqual(payload["vehicle_make"], "Volvo")
        self.assertEqual(payload["vehicle_type"], "XC60")
        self.assertEqual(payload["vehicle_color"], "Gra")


if __name__ == "__main__":
    unittest.main()
