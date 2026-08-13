import json

from roborock_logger.app import main as logger


def test_resend_queue_quarantines_bad_lines_without_blocking_valid_batches(tmp_path, monkeypatch):
    queue_file = tmp_path / "pending_batches.jsonl"
    error_file = tmp_path / "pending_batches.invalid.jsonl"
    valid = {"endpoint": "/api/renhold/ingest", "payload": {"robots": [{"duid": "one"}]}}
    queue_file.write_text("not-json\n" + json.dumps(valid) + "\n", encoding="utf-8")
    sent = []
    monkeypatch.setattr(logger, "DATA_DIR", tmp_path)
    monkeypatch.setattr(logger, "QUEUE_FILE", queue_file)
    monkeypatch.setattr(logger, "QUEUE_ERROR_FILE", error_file)
    monkeypatch.setattr(logger, "post_to_fibaro10", lambda batch, endpoint: sent.append((batch, endpoint)))

    assert logger.resend_queue() == 1
    assert sent == [(valid["payload"], valid["endpoint"])]
    assert queue_file.read_text(encoding="utf-8") == ""
    quarantined = json.loads(error_file.read_text(encoding="utf-8").strip())
    assert quarantined["raw_line"] == "not-json"


def test_regular_sync_reuses_known_hosts_until_discovery_is_needed():
    devices = [{"duid": "one"}, {"duid": "two"}]
    healthy_state = {"robots": {"one": {"local_ip": "192.168.2.10"}, "two": {"local_ip": "192.168.2.11"}}}

    assert logger.should_scan_hosts(
        {"_cache": {"source": "file"}},
        devices,
        ["192.168.2.10", "192.168.2.11"],
        healthy_state,
        force_home_refresh=False,
    ) is False
    assert logger.should_scan_hosts(
        {"_cache": {"source": "cloud"}},
        devices,
        ["192.168.2.10", "192.168.2.11"],
        healthy_state,
        force_home_refresh=False,
    ) is True


def test_sync_scans_again_after_local_telemetry_failure_or_new_robot():
    devices = [{"duid": "one"}, {"duid": "two"}]
    failed_state = {"robots": {"one": {"last_telemetry_error": "timeout"}}}

    assert logger.should_scan_hosts(
        {"_cache": {"source": "file"}},
        devices,
        ["192.168.2.10", "192.168.2.11"],
        failed_state,
        force_home_refresh=False,
    ) is True
    assert logger.should_scan_hosts(
        {"_cache": {"source": "file"}},
        devices,
        ["192.168.2.10"],
        {"robots": {}},
        force_home_refresh=False,
    ) is True
