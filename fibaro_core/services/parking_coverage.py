"""Conservative payment coverage of camera observation intervals, not occupancy proof."""

from time_formatting import api_local_iso, normalize_local_naive, parse_datetime
from value_parsing import float_or_zero


def observed_payment_coverage(first, last, parkings, imported_through=None):
    first = normalize_local_naive(parse_datetime(first)) if isinstance(first, str) else normalize_local_naive(first)
    last = normalize_local_naive(parse_datetime(last)) if isinstance(last, str) else normalize_local_naive(last)
    result = {"status": "unknown", "label": "Ukjent tidsgrunnlag", "coveredMinutes": 0.0, "uncoveredMinutes": None, "matches": []}
    if first is None or last is None or last <= first:
        return result
    intervals = []
    uncertain = False
    for parking in parkings:
        if float_or_zero(parking.fee_inc_vat) <= 0:
            continue
        start = normalize_local_naive(parking.start_time)
        end = normalize_local_naive(parking.end_time)
        if start is None or start >= last:
            continue
        if end is None:
            uncertain |= start.date() == first.date()
            continue
        if end <= first or end <= start:
            continue
        intervals.append((max(start, first), min(end, last)))
        result["matches"].append({"id": getattr(parking, "id", None), "start": api_local_iso(start), "end": api_local_iso(end), "amount": float_or_zero(parking.fee_inc_vat)})
    cursor = first
    seconds = 0
    for start, end in sorted(intervals):
        if end > max(start, cursor):
            seconds += (end - max(start, cursor)).total_seconds()
        cursor = max(cursor, end)
    duration = (last - first).total_seconds()
    result.update(coveredMinutes=round(seconds / 60, 1), uncoveredMinutes=round((duration - seconds) / 60, 1))
    cutoff = normalize_local_naive(imported_through)
    if seconds >= duration:
        result.update(status="covered", label="Dekket av registrert betaling")
    elif cutoff is None or cutoff < last:
        result.update(status="pending", label="Venter på betalingsgrunnlag")
    elif uncertain:
        result.update(status="unknown", label="Betaling uten sluttid")
    elif seconds:
        result.update(status="partial", label="Delvis betalingsdekning")
    else:
        result.update(status="unmatched", label="Ingen samsvarende betaling")
    return result
