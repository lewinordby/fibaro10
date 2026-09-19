"""Synthetic desktop API payload for mobile layout and regression checks."""


def revenue_preview():
    periods = []
    for key, title, factor, previous, extra, full in (
        ("today", "I dag", 1, "i går", "samme dag forrige uke", "Hele samme dag forrige uke"),
        ("week", "Denne uke", 6, "forrige uke", "samme uke 2025", "Hele samme uke 2025"),
        ("month", "Denne måned", 24, "forrige måned", "samme måned 2025", "Hele samme måned 2025"),
        ("year", "Dette år", 310, "i 2025", "i 2024", "Hele 2024"),
    ):
        periods.append({
            "key": key, "title": title,
            "total": 11840 * factor, "sol": 4120 * factor, "parking": 7720 * factor,
            "solCount": 20 * factor, "parkingCount": 42 * factor,
            "rank": {"label": "5. beste", "basis": "Rangert mot hele historiske perioder"},
            "solAsOfLabel": "kl 14:27", "parkingAsOfLabel": "kl 14:00",
            "previousLabel": "Sammenlignet med tilsvarende datatidspunkt " + previous,
            "previousFullLabel": "Hele " + previous,
            "previousSol": 3820 * factor, "previousParking": 7100 * factor,
            "previousTotal": 10920 * factor, "previousFullTotal": 13600 * factor,
            "extraComparisons": [{
                "label": "Sammenlignet med " + extra, "fullLabel": full,
                "sol": 4220 * factor, "parking": 8260 * factor,
                "total": 12480 * factor, "fullTotal": 14150 * factor,
            }],
        })
    return {
        "generatedAt": "2026-09-19T14:30:00+02:00", "statusPeriods": periods,
        "services": [{"jobName": "easypark_parking_import", "nextExpectedAt": "2026-09-19T16:00:00+02:00"}],
    }
