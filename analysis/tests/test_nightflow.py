import numpy as np
from jalnaadi import nightflow, priority, payload


def test_detects_leak_quickly():
    rng = np.random.default_rng(3)
    q = nightflow.synth_night_series(days=80, leak_start=40, leak_dq=0.3, rng=rng)
    first, _ = nightflow.run_series(q)
    assert first is not None and 40 <= first <= 44


def test_quiet_zone_stays_quiet():
    rng = np.random.default_rng(10)
    q = nightflow.synth_night_series(days=60, rng=rng)
    first, _ = nightflow.run_series(q)
    assert first is None


def test_priority_ranking():
    ranked = priority.rank([
        {"id": "A", "excess_m3h": 0.1, "households": 400},
        {"id": "B", "excess_m3h": 0.5, "households": 100},
    ])
    assert ranked[0]["id"] == "B"
    assert ranked[0]["loss_lpd"] == 9600


def test_payload_is_compact():
    p = payload.build_payload("G01", "E07", "ear", payload.leak_event_params(6.0, 20.0, 400, 31.2, "S3"), ts=1)
    assert len(payload.to_json(p)) < 140
