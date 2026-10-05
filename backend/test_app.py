import os, tempfile
os.environ["JALNAADI_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
import numpy as np
from fastapi.testclient import TestClient
import app as appmod

client = TestClient(appmod.app)


def test_end_to_end():
    client.post("/segments", json=dict(seg="S1", zone="Z1", lat1=19.0, lon1=72.0, lat2=19.001, lon2=72.0, length_m=100.0, households=120))
    rng = np.random.default_rng(1)
    alarm_resp = None
    for d in range(60):
        q = 0.40 + rng.normal(0, 0.03) + (0.3 if d >= 40 else 0)
        r = client.post("/ingest", json=dict(gid="G1", did="GATE1", dty="gate", dt=86400 * d, p=dict(zone="Z1", qn=q))).json()
        if r["alarm"] and alarm_resp is None:
            alarm_resp = (d, r)
    assert alarm_resp and 40 <= alarm_resp[0] <= 44
    r = client.post("/ingest", json=dict(gid="G1", did="EAR1", dty="ear", dt=1, p=dict(seg="S1", x=25.0, L=100.0, v=400, cf=30.0, cls="leak")))
    assert r.json()["stored"]
    leaks = client.get("/leaks").json()
    assert len(leaks) == 1 and abs(leaks[0]["lat"] - 19.00025) < 1e-6 and leaks[0]["loss_lpd"] > 0


def test_non_leak_class_is_not_stored():
    r = client.post("/ingest", json=dict(gid="G1", did="EAR1", dty="ear", dt=2, p=dict(seg="S1", x=5.0, L=100.0, v=400, cf=3.0, cls="pump")))
    assert r.json()["stored"] is False
