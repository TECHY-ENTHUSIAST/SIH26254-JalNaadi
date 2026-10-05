"""NAADI-DESK backend: ingest NJJM-style payloads, screen zones, place leaks on the map, rank repairs.

Run:  uvicorn app:app --reload        (from this folder; needs ../analysis on PYTHONPATH)
"""
import os, sys, sqlite3, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analysis"))
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from jalnaadi.nightflow import NightFlowDetector
from jalnaadi import priority

DB = os.environ.get("JALNAADI_DB", os.path.join(os.path.dirname(__file__), "jalnaadi.db"))
app = FastAPI(title="JalNaadi DESK", version="0.1.0")
_detectors: dict[str, NightFlowDetector] = {}


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE IF NOT EXISTS segments(seg TEXT PRIMARY KEY, zone TEXT, lat1 REAL, lon1 REAL, lat2 REAL, lon2 REAL, length_m REAL, households INTEGER, sujal_gaon_id TEXT);
    CREATE TABLE IF NOT EXISTS nights(zone TEXT, dt INTEGER, q REAL);
    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, seg TEXT, did TEXT, dt INTEGER, x REAL, v REAL, cf REAL, cls TEXT);
    """)
    return c


class Segment(BaseModel):
    seg: str; zone: str
    lat1: float; lon1: float; lat2: float; lon2: float
    length_m: float; households: int; sujal_gaon_id: str = ""


class Payload(BaseModel):
    gid: str; did: str; dty: str; dt: int; p: dict


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/segments")
def add_segment(s: Segment):
    with db() as c:
        c.execute("INSERT OR REPLACE INTO segments VALUES (?,?,?,?,?,?,?,?,?)",
                  (s.seg, s.zone, s.lat1, s.lon1, s.lat2, s.lon2, s.length_m, s.households, s.sujal_gaon_id))
    return {"ok": True}


@app.post("/ingest")
def ingest(pl: Payload):
    with db() as c:
        if pl.dty == "gate":                                   # nightly mean flow of a zone
            zone, q = pl.p["zone"], float(pl.p["qn"])
            c.execute("INSERT INTO nights VALUES (?,?,?)", (zone, pl.dt, q))
            det = _detectors.setdefault(zone, NightFlowDetector())
            st = det.update(q)
            return {"zone": zone, **st, "excess_m3h": det.excess_flow(q) if st["alarm"] else 0.0}
        if pl.dty == "ear":                                    # located leak from a node pair
            p = pl.p
            if p.get("cls") != "leak":
                return {"stored": False, "reason": "classified " + str(p.get("cls"))}
            c.execute("INSERT INTO events(seg,did,dt,x,v,cf,cls) VALUES (?,?,?,?,?,?,?)",
                      (p["seg"], pl.did, pl.dt, p["x"], p["v"], p["cf"], p["cls"]))
            return {"stored": True}
    raise HTTPException(400, "unknown device type")


@app.get("/leaks")
def leaks():
    """Latest located leak per segment, with map position and repair priority."""
    out = []
    with db() as c:
        for e in c.execute("SELECT * FROM events WHERE id IN (SELECT MAX(id) FROM events GROUP BY seg)"):
            s = c.execute("SELECT * FROM segments WHERE seg=?", (e["seg"],)).fetchone()
            if not s:
                continue
            f = min(max(e["x"] / s["length_m"], 0.0), 1.0)
            det = _detectors.get(s["zone"])
            last = c.execute("SELECT q FROM nights WHERE zone=? ORDER BY dt DESC LIMIT 1", (s["zone"],)).fetchone()
            excess = det.excess_flow(last["q"]) if (det and last and det.alarm) else 0.0
            out.append({"seg": e["seg"], "zone": s["zone"], "x_m": e["x"], "confidence": e["cf"], "households": s["households"],
                        "lat": s["lat1"] + f * (s["lat2"] - s["lat1"]), "lon": s["lon1"] + f * (s["lon2"] - s["lon1"]),
                        "excess_m3h": round(excess, 3), "sujal_gaon_id": s["sujal_gaon_id"]})
    return priority.rank(out)
