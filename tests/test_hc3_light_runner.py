from pathlib import Path


def test_light_runner_controls_both_facade_light_strips():
    lua = Path("scripts/hc3_light_runner_scene_362.lua").read_text(encoding="utf-8")

    assert 'configKey = "lyslist"' in lua
    assert "deviceIds = {425, 298}" in lua
    assert "lightDeviceIds" in lua
    assert "allDevicesOn" in lua
    assert "anyDeviceOn" in lua


def test_fibaro10_light_config_knows_new_facade_light_id():
    source = Path("main.py").read_text(encoding="utf-8")

    assert '"key": "lyslist", "name": "Lyslist dekor", "sample_attr": "light_lyslist", "legacy_ids": [425, 298]' in source
    assert '"device_ids": [425, 298]' in source
