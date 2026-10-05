"""Payload helpers. Field layout (gid / did / dty / dt / p) is modelled on the NJJM Technical Expert
Committee reference payload; align field codes with the latest NJJM specification before field use."""
from __future__ import annotations
import json, time


def build_payload(gid, did, dty, params, ts=None):
    return {"gid": gid, "did": did, "dty": dty, "dt": int(ts or time.time()), "p": params}


def leak_event_params(x_m, L_m, v_ms, confidence, seg_id, cls="leak"):
    """Compact result sent by the pair-master node over LoRa (a few tens of bytes)."""
    return {"seg": seg_id, "x": round(x_m, 2), "L": round(L_m, 1), "v": round(v_ms), "cf": round(confidence, 1), "cls": cls}


def to_json(payload):
    return json.dumps(payload, separators=(",", ":"))
