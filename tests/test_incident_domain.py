from datetime import datetime, timedelta
from pathlib import Path

from incident_domain import (
    apply_incident_reviews,
    backup_control,
    incident_summary,
    operational_incident,
    parse_status_text,
)
from observability import STORAGE_TABLES


def test_parse_status_text_ignores_comments_and_invalid_lines() -> None:
    assert parse_status_text("# status\nstatus=ok\nfinished=20260807-031500\ninvalid") == {
        "status": "ok",
        "finished": "20260807-031500",
    }


def test_backup_control_marks_fresh_backup_ok() -> None:
    now = datetime(2026, 8, 7, 12, 0)
    row = backup_control(
        key="backup-nightly",
        title="Nattbackup",
        values={"status": "ok", "finished": "20260807-031500"},
        now=now,
        warning_after_hours=24,
        critical_after_hours=26,
    )
    assert row["status"] == "ok"
    assert row["ageHours"] == 8.8


def test_backup_control_marks_missing_and_old_backup_critical() -> None:
    now = datetime(2026, 8, 7, 12, 0)
    missing = backup_control(
        key="missing",
        title="Mangler",
        values={},
        now=now,
        warning_after_hours=24,
        critical_after_hours=26,
    )
    old = backup_control(
        key="old",
        title="Gammel",
        values={"status": "ok", "finished": "20260805-010000"},
        now=now,
        warning_after_hours=24,
        critical_after_hours=26,
    )
    assert missing["status"] == "critical"
    assert old["status"] == "critical"


def test_review_only_applies_to_current_incident_occurrence() -> None:
    started = datetime(2026, 8, 7, 10, 0)
    incident = operational_incident(
        key="source:easypark",
        domain="Datakilder",
        title="EasyPark",
        detail="Feil",
        severity="critical",
        source="Import",
        started_at=started,
    )
    acknowledged = apply_incident_reviews(
        [incident],
        {
            "source:easypark": {
                "status": "acknowledged",
                "reviewed_at": started + timedelta(minutes=5),
                "reviewed_by": "master",
                "note": "Følges opp",
            }
        },
    )[0]
    stale_review = apply_incident_reviews(
        [incident],
        {"source:easypark": {"status": "acknowledged", "reviewed_at": started - timedelta(minutes=1)}},
    )[0]
    assert acknowledged["reviewState"] == "acknowledged"
    assert acknowledged["reviewNote"] == "Følges opp"
    assert stale_review["reviewState"] == "open"


def test_incident_summary_counts_attention_and_reviews() -> None:
    rows = [
        {"domain": "Dører", "severity": "critical", "reviewState": "open"},
        {"domain": "Dører", "severity": "warning", "reviewState": "acknowledged"},
        {"domain": "Backup", "severity": "info", "reviewState": "open"},
    ]
    assert incident_summary(rows) == {
        "active": 3,
        "critical": 1,
        "warning": 1,
        "info": 1,
        "acknowledged": 1,
        "unreviewed": 2,
        "domains": 2,
    }


def test_incident_review_storage_and_migration_are_registered() -> None:
    migration = Path(
        "migrations/versions/20260807_1800_add_operational_incident_reviews.sql"
    ).read_text(encoding="utf-8")
    assert "operational_incident_reviews" in STORAGE_TABLES
    assert "CREATE TABLE IF NOT EXISTS operational_incident_reviews" in migration
    assert "incident_key VARCHAR NOT NULL UNIQUE" in migration
