"""NAADI-DESK: convert night-flow excess into litres/day and rank repairs."""
from __future__ import annotations

PRESSURE_FACTOR = 0.8   # night pressure is higher than the daily mean, so the night leak rate overstates the 24 h average


def litres_per_day(excess_m3h, factor=PRESSURE_FACTOR):
    return excess_m3h * 1000.0 * 24.0 * factor


def priority_score(loss_lpd, households):
    return loss_lpd * households


def rank(leaks):
    """leaks: list of dicts with excess_m3h and households. Returns list sorted by score, highest first."""
    out = []
    for lk in leaks:
        loss = litres_per_day(lk["excess_m3h"])
        out.append({**lk, "loss_lpd": round(loss), "score": round(priority_score(loss, lk["households"]))})
    return sorted(out, key=lambda d: d["score"], reverse=True)
