from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime
import json
import math
from typing import Any, Dict, Mapping, Optional
from zoneinfo import ZoneInfo

from dateutil import parser as dtparser

from parking_vehicle_helpers import compact_plate


LOCAL_TZ = ZoneInfo("Europe/Oslo")


def _int_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _local_iso(value: Optional[datetime]) -> Optional[str]:
    if not value:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=LOCAL_TZ).isoformat()
    return value.astimezone(LOCAL_TZ).isoformat()


def cars_recognition_local_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        try:
            parsed = dtparser.isoparse(str(value))
        except (TypeError, ValueError, OverflowError):
            return None
    else:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return parsed.replace(tzinfo=None)


def cars_detection_is_covered(
    detection_at: Optional[datetime],
    parking_start_at: Optional[datetime],
    parking_end_at: Optional[datetime],
) -> bool:
    return bool(
        detection_at
        and parking_start_at
        and parking_end_at
        and parking_start_at <= detection_at <= parking_end_at
    )


def cars_unifi_score(value: Any) -> Optional[float]:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(score):
        return None
    return round(max(0.0, min(100.0, score)), 1)


def cars_confidence_level(score: Optional[float]) -> str:
    if score is None:
        return "unscored"
    if score >= 80:
        return "high"
    if score >= 60:
        return "medium"
    return "low"


def cars_plate_edit_distance(left: str, right: str) -> int:
    left_value = compact_plate(left)
    right_value = compact_plate(right)
    if len(left_value) > len(right_value):
        left_value, right_value = right_value, left_value
    previous = list(range(len(left_value) + 1))
    for right_index, right_character in enumerate(right_value, start=1):
        current = [right_index]
        for left_index, left_character in enumerate(left_value, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[left_index] + 1,
                    previous[left_index - 1] + (left_character != right_character),
                )
            )
        previous = current
    return previous[-1]


def cars_likely_ocr_variants(
    left_plate: str,
    right_plate: str,
    left_evidence: list[tuple[datetime, str]],
    right_evidence: list[tuple[datetime, str]],
    *,
    maximum_seconds: int = 120,
) -> bool:
    left_value = compact_plate(left_plate)
    right_value = compact_plate(right_plate)
    if left_value == right_value or min(len(left_value), len(right_value)) < 5:
        return False
    maximum_length = max(len(left_value), len(right_value))
    if abs(len(left_value) - len(right_value)) > 2:
        return False
    distance_limit = 1 if maximum_length <= 6 else 2
    if cars_plate_edit_distance(left_value, right_value) > distance_limit:
        return False
    return any(
        left_camera
        and left_camera == right_camera
        and abs((left_at - right_at).total_seconds()) <= maximum_seconds
        for left_at, left_camera in left_evidence
        for right_at, right_camera in right_evidence
    )


def cars_group_daily_recognitions(recognition_items: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """Group only Ledger-confirmed OCR variants under a validated daily plate."""
    by_plate = {
        compact_plate(item.get("plate") or item.get("display_value")): item
        for item in recognition_items
        if compact_plate(item.get("plate") or item.get("display_value"))
    }
    grouped: Dict[str, list[tuple[str, Dict[str, Any]]]] = defaultdict(list)
    for raw_plate, item in by_plate.items():
        canonical_plate = compact_plate(item.get("likely_canonical_plate"))
        canonical_item = by_plate.get(canonical_plate)
        canonical_validation = (
            canonical_item.get("validation")
            if canonical_item and isinstance(canonical_item.get("validation"), dict)
            else {}
        )
        raw_validation = item.get("validation") if isinstance(item.get("validation"), dict) else {}
        can_merge = bool(
            item.get("is_likely_ocr_variant")
            and canonical_plate
            and canonical_plate != raw_plate
            and canonical_item
            and canonical_validation.get("is_valid") is True
            and raw_validation.get("is_valid") is not True
        )
        grouped[canonical_plate if can_merge else raw_plate].append((raw_plate, item))

    result: list[Dict[str, Any]] = []
    for plate_value, members in grouped.items():
        canonical_source = next((item for raw_plate, item in members if raw_plate == plate_value), members[0][1])
        combined = deepcopy(canonical_source)
        observed_values = sorted({raw_plate for raw_plate, _ in members})
        detections: list[Dict[str, Any]] = []
        detection_times: list[Any] = []
        camera_names: set[str] = set()
        known_in_protect = False
        for raw_plate, member in members:
            known_in_protect = known_in_protect or bool(member.get("known_in_protect"))
            camera_names.update(str(name) for name in member.get("camera_names") or [] if name)
            detection_times.extend(member.get("detection_times") or [])
            raw_detections = member.get("detections") or []
            if isinstance(raw_detections, str):
                try:
                    raw_detections = json.loads(raw_detections)
                except (TypeError, ValueError):
                    raw_detections = []
            for detection in raw_detections:
                if not isinstance(detection, dict):
                    continue
                evidence = dict(detection)
                evidence["observed_plate"] = raw_plate
                detections.append(evidence)

        detections.sort(
            key=lambda detection: (
                cars_recognition_local_datetime(detection.get("occurred_at")) or datetime.min,
                _int_or_zero(detection.get("recognition_id")),
            )
        )
        combined.update(
            {
                "plate": plate_value,
                "display_value": canonical_source.get("display_value") or plate_value,
                "detection_count": sum(_int_or_zero(member.get("detection_count")) for _, member in members)
                or len(detections),
                "detections": detections,
                "detection_times": sorted(detection_times, key=lambda value: str(value)),
                "camera_names": sorted(camera_names),
                "known_in_protect": known_in_protect,
                "observed_plate_values": observed_values,
                "merged_variant_count": max(0, len(observed_values) - 1),
                "likely_canonical_plate": plate_value,
                "is_likely_ocr_variant": False,
            }
        )
        result.append(combined)
    return result


def cars_public_detection(detection: Mapping[str, Any], plate_value: str) -> Dict[str, Any]:
    occurred_at = cars_recognition_local_datetime(detection.get("occurred_at"))
    source_event_id = str(detection.get("source_event_id") or "").strip()
    recognition_id = detection.get("recognition_id")
    return {
        "recognitionId": recognition_id,
        "occurredAt": _local_iso(occurred_at),
        "cameraId": detection.get("camera_id"),
        "cameraName": detection.get("camera_name"),
        "observedPlate": compact_plate(detection.get("observed_plate")) or plate_value,
        "sourceEventId": source_event_id or None,
        "unifiScore": cars_unifi_score(detection.get("unifi_score")),
        "snapshotStatus": detection.get("snapshot_status"),
        "snapshotCapturedAt": detection.get("snapshot_captured_at"),
        "snapshotTargetAt": detection.get("snapshot_target_at"),
        "snapshotTimeOffsetMs": detection.get("snapshot_time_offset_ms"),
        "snapshotSource": detection.get("snapshot_source"),
        "snapshotCameraId": detection.get("snapshot_camera_id"),
        "snapshotUrl": (
            f"/api/unifi-protect/recognitions/{int(recognition_id)}/snapshot"
            if recognition_id is not None and detection.get("snapshot_url")
            else None
        ),
    }


def cars_daily_payment_metrics(
    detection_datetimes: list[datetime],
    paid_sessions: list[Dict[str, Any]],
) -> Dict[str, Any]:
    covered_detection_count = sum(
        1
        for detected_at in detection_datetimes
        if any(
            cars_detection_is_covered(detected_at, parking.get("_startAt"), parking.get("_endAt"))
            for parking in paid_sessions
        )
    )
    if not paid_sessions:
        return {
            "coveredDetectionCount": 0,
            "dayMatchedDetectionCount": 0,
            "firstPaymentAt": None,
            "lastPaymentEndAt": None,
            "minutesBeforeFirstPayment": None,
            "minutesAfterLastPayment": None,
            "paymentStatus": "no_payment",
        }

    payment_starts = [row.get("_startAt") for row in paid_sessions if row.get("_startAt")]
    payment_ends = [row.get("_endAt") for row in paid_sessions if row.get("_endAt")]
    first_payment_at = min(payment_starts) if payment_starts else None
    last_payment_end_at = max(payment_ends) if payment_ends else None
    first_detection_at = min(detection_datetimes) if detection_datetimes else None
    last_detection_at = max(detection_datetimes) if detection_datetimes else None
    minutes_before_first_payment = (
        round(max(0.0, (first_payment_at - first_detection_at).total_seconds() / 60), 1)
        if first_payment_at and first_detection_at
        else None
    )
    minutes_after_last_payment = (
        round(max(0.0, (last_detection_at - last_payment_end_at).total_seconds() / 60), 1)
        if last_payment_end_at and last_detection_at
        else None
    )
    return {
        "coveredDetectionCount": covered_detection_count,
        "dayMatchedDetectionCount": len(detection_datetimes),
        "firstPaymentAt": _local_iso(first_payment_at),
        "lastPaymentEndAt": _local_iso(last_payment_end_at),
        "minutesBeforeFirstPayment": minutes_before_first_payment,
        "minutesAfterLastPayment": minutes_after_last_payment,
        "paymentStatus": "paid_same_day",
    }
