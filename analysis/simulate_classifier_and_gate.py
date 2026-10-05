"""Synthetic studies for the on-node classifier and the GATE night-flow detector (SIMULATION only)."""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(__file__))
from jalnaadi import dsp, nightflow

BLUE, GREEN, ORANGE, NAVY, RED = "#0070C0", "#1E7B34", "#E8731A", "#1F4E79", "#C01F1F"
OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "images")
FS, N = 4000, 4000 * 4
CLASSES = ["leak", "pump", "tap", "quiet"]


def make(rng, kind):
    t = np.arange(N) / FS
    white = rng.standard_normal(N)
    if kind == "leak":
        fc, bw = rng.uniform(150, 500), rng.uniform(150, 400)
        x = dsp.bandpass(white, FS, max(50, fc - bw / 2), min(1000, fc + bw / 2))
        x = x / np.std(x) * rng.uniform(0.5, 1.5)
        snr = rng.uniform(3, 20)
        x = x + rng.standard_normal(N) * (np.std(x) / 10 ** (snr / 20))
    elif kind == "pump":
        f0 = rng.uniform(46, 52)
        x = sum((1.0 / h) * np.sin(2 * np.pi * f0 * h * t + rng.uniform(0, 6.28)) for h in range(1, 9))
        x = x / np.std(x) * rng.uniform(0.5, 1.5)
        x = x + rng.standard_normal(N) * (np.std(x) / 10 ** (rng.uniform(10, 25) / 20))
    elif kind == "tap":
        x = rng.standard_normal(N) * rng.uniform(0.04, 0.08)
        for _ in range(rng.integers(3, 7)):
            s0 = rng.integers(0, N - 1200); L_ = rng.integers(300, 1200)
            burst = dsp.bandpass(rng.standard_normal(L_), FS, 80, 900) * np.hanning(L_)
            x[s0:s0 + L_] += burst / np.std(burst) * rng.uniform(1.0, 3.0)
    else:
        x = rng.standard_normal(N) * rng.uniform(0.03, 0.08)
    return x


def main(n=300):
    rng = np.random.default_rng(7)
    conf = np.zeros((4, 4), int)
    feats = {c: [] for c in CLASSES}
    for i, c in enumerate(CLASSES):
        for _ in range(n):
            f = dsp.features(make(rng, c), FS)
            feats[c].append(f)
            conf[i, CLASSES.index(dsp.classify(f, rms_floor=0.12))] += 1
    acc = float(np.trace(conf) / conf.sum() * 100)
    print("classifier accuracy %.1f%%" % acc); print(conf)

    # GATE night-flow study: detection delay vs leak size, false alarm rate
    rng = np.random.default_rng(11)
    gate = {}
    for dq in [0.1, 0.2, 0.3, 0.5]:
        delays = []
        for _ in range(300):
            q = nightflow.synth_night_series(days=90, leak_start=40, leak_dq=dq, rng=rng)
            first, _s = nightflow.run_series(q)
            if first is not None and first < 40:
                continue                      # false alarm before the leak: excluded here, counted below
            delays.append(np.nan if first is None else first - 40)
        d = np.array(delays)
        gate[str(dq)] = dict(detected=float(np.mean(~np.isnan(d)) * 100), median_delay=float(np.nanmedian(d)) if np.any(~np.isnan(d)) else None,
                             p90_delay=float(np.nanpercentile(d, 90)) if np.any(~np.isnan(d)) else None,
                             L_per_min=round(dq * 1000 / 60, 1), L_per_day=int(dq * 24000))
    events, exposure = 0, 0
    for _ in range(600):
        q = nightflow.synth_night_series(days=90, rng=rng)
        first, _s = nightflow.run_series(q)
        events += first is not None
        exposure += (first if first is not None else 90)
    gate["nights_per_false_alarm"] = float(exposure / max(events, 1))
    print(gate)
    json.dump(dict(classifier=dict(accuracy=acc, confusion=conf.tolist(), classes=CLASSES), gate=gate),
              open(os.path.join(OUT, "..", "classifier_gate_results.json"), "w"), indent=1)

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(4.6, 3.8))
    ax.imshow(conf / conf.sum(1, keepdims=True), cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(4)); ax.set_xticklabels(CLASSES); ax.set_yticks(range(4)); ax.set_yticklabels(CLASSES)
    ax.set_xlabel("classified as"); ax.set_ylabel("true source")
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{conf[i, j] / conf[i].sum() * 100:.0f}%", ha="center", va="center", color="white" if conf[i, j] / conf[i].sum() > .5 else "black")
    ax.set_title(f"On-node classifier on synthetic signals ({acc:.0f}% overall)", fontsize=9, color=NAVY)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "sim_classifier.png"), dpi=170); plt.close(fig)

    rng = np.random.default_rng(5)
    q = nightflow.synth_night_series(days=90, leak_start=40, leak_dq=0.2, rng=rng)
    first, st = nightflow.run_series(q)
    fig, ax = plt.subplots(2, 1, figsize=(7.2, 4.4), sharex=True)
    ax[0].plot(q, color=BLUE, lw=1, label="night flow 02:00–04:00 (m³/h)")
    ax[0].plot([s["baseline"] for s in st], color=ORANGE, lw=1.6, label="learned baseline (EWMA)")
    ax[0].axvline(40, color="#888", ls=":"); ax[0].text(40.5, q.max() * 0.98, "leak starts (+0.2 m³/h ≈ 3.3 L/min)", fontsize=8)
    ax[0].legend(frameon=False, fontsize=8, loc="upper left"); ax[0].set_ylabel("m³/h")
    ax[1].plot([s["cusum"] for s in st], color=GREEN, lw=1.4); ax[1].axhline(5, color=RED, ls="--", lw=1)
    ax[1].text(1, 5.3, "alarm threshold h = 5", color=RED, fontsize=8)
    if first is not None: ax[1].axvline(first, color=RED, lw=1); ax[1].text(first + .5, 1, f"alarm: night {first}", color=RED, fontsize=8)
    ax[1].set_xlabel("night"); ax[1].set_ylabel("CUSUM")
    fig.suptitle("NAADI-GATE on a synthetic zone", fontsize=10, color=NAVY)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "sim_gate.png"), dpi=170); plt.close(fig)


if __name__ == "__main__":
    main()
