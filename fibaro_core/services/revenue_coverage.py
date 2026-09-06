"""Coverage indicators describe evidence, never claim that an import proves completeness."""

from datetime import datetime, time, timedelta
from time_formatting import api_local_iso, normalize_local_naive


def month_source_coverage(start, end, today, source_days, last_success):
    last_success = normalize_local_naive(last_success)
    elapsed_end = min(end, today + timedelta(days=1))
    elapsed = max(0, (elapsed_end - start).days)
    present = sorted(day for day in source_days if start <= day < elapsed_end)
    missing = [start + timedelta(days=index) for index in range(elapsed) if start + timedelta(days=index) not in source_days]
    return {
        "daysWithRecords": len(present), "elapsedDays": elapsed,
        "daysWithoutRecords": [day.isoformat() for day in missing],
        "lastSuccessfulImport": api_local_iso(last_success) if last_success else None,
        "status": "ongoing" if start <= today < end else "future" if start > today
            else "unknown" if last_success is None or last_success < datetime.combine(end, time.min)
            else "review" if missing else "recorded",
    }
