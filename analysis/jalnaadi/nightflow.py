"""NAADI-GATE: night-flow screening with a learned baseline (EWMA) and a CUSUM change detector."""
from __future__ import annotations
import numpy as np


class NightFlowDetector:
    """Feed one number per night: mean zone inlet flow in the 02:00-04:00 window (m3/h).

    * First `warmup` nights learn the baseline mean and spread.
    * Afterwards the baseline follows slow, legitimate drift (EWMA) but freezes while a change is
      building, so a developing leak cannot be 'learned away'.
    * Deviations are standardised and accumulated by a one-sided CUSUM; alarm == leak suspected in this zone.
    """

    def __init__(self, lam=0.1, k=0.75, h=5.0, warmup=14, sigma_floor=0.7):
        self.lam, self.k, self.h, self.warmup, self.sigma_floor = lam, k, h, warmup, sigma_floor
        self.hist, self.n = [], 0
        self.base = self.sigma0 = self.var = None
        self.S, self.alarm = 0.0, False

    def update(self, q):
        self.n += 1
        if self.n <= self.warmup:
            self.hist.append(q)
            if self.n == self.warmup:
                self.base = float(np.mean(self.hist))
                self.sigma0 = max(float(np.std(self.hist, ddof=1)), 1e-6)
                self.var = self.sigma0 ** 2
            return self.state()
        sigma = max(np.sqrt(self.var), self.sigma_floor * self.sigma0)
        z = (q - self.base) / sigma
        self.S = max(0.0, self.S + z - self.k)
        self.alarm = bool(self.S > self.h)
        if self.S < 0.5 * self.h and not self.alarm:           # learn only while no change is building
            self.var = (1 - self.lam) * self.var + self.lam * (q - self.base) ** 2   # innovation vs previous baseline
            self.base = (1 - self.lam) * self.base + self.lam * q
        return self.state()

    def state(self):
        return dict(baseline=None if self.base is None else float(self.base), cusum=float(self.S), alarm=bool(self.alarm))

    def excess_flow(self, q):
        """Estimated leak flow (m3/h) = current night flow minus learned baseline."""
        return float(max(0.0, q - (self.base if self.base is not None else q)))


def synth_night_series(days=70, q0=0.40, sigma_day=0.035, ar=0.3, leak_start=None, leak_dq=0.0, rng=None):
    """Synthetic nightly means (m3/h) with day-to-day AR(1) variation and an optional step leak."""
    rng = rng or np.random.default_rng()
    q = np.zeros(days)
    e = 0.0
    for d in range(days):
        e = ar * e + rng.normal(0, sigma_day)
        q[d] = q0 + e + (leak_dq if (leak_start is not None and d >= leak_start) else 0.0)
    return q


def run_series(q, **kw):
    det = NightFlowDetector(**kw)
    first, states = None, []
    for d, v in enumerate(q):
        s = det.update(v)
        states.append(s)
        if s["alarm"] and first is None:
            first = d
    return first, states
