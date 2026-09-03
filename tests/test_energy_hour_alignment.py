from datetime import timedelta

from fibaro_core.catalog import ENERGY_HC3_HOURLY_DISPLAY_OFFSET


def test_hc3_energy_uses_same_local_hour_as_elvia():
    assert ENERGY_HC3_HOURLY_DISPLAY_OFFSET == timedelta(0)
