"""Monte-Carlo study of NAADI-EAR localisation (SIMULATION, not a hardware measurement).

Run:  python simulate_localisation.py   -> writes ../docs/images/sim_*.png and ../docs/simulation_results.json
"""
import json, sys, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(__file__))
from jalnaadi import dsp

BLUE, GREEN, ORANGE, NAVY, RED = "#0070C0", "#1E7B34", "#E8731A", "#1F4E79", "#C01F1F"
FS = 4000
DUR = 10.0
OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "images")
os.makedirs(OUT, exist_ok=True)


def one_trial(rng, L=8.0, v=400.0, x=None, snr_db=5.0, sync_sigma_ms=0.3, atten_len=20.0,
              bits=16, v_assumed=None, tap_calibrate=False):
    x = x if x is not None else rng.uniform(0.1 * L, 0.9 * L)
    n = int(FS * DUR)
    src = dsp.bandpass(rng.standard_normal(n), FS)
    src /= np.std(src)
    dA, dB = x, L - x
    a = np.exp(-dA / atten_len) * dsp.fractional_delay(src, dA / v, FS)
    b = np.exp(-dB / atten_len) * dsp.fractional_delay(src, dB / v, FS)
    amid = np.exp(-(L / 2) / atten_len)
    sig = amid / (10 ** (snr_db / 20.0))
    a = a + sig * dsp.bandpass(rng.standard_normal(n), FS, 20, 1900)
    b = b + sig * dsp.bandpass(rng.standard_normal(n), FS, 20, 1900)
    e = rng.normal(0, sync_sigma_ms * 1e-3)                     # residual sync error between the nodes
    b = dsp.fractional_delay(b, e, FS)
    a, b = dsp.quantise(a, bits), dsp.quantise(b, bits)
    tau, ratio = dsp.gcc_phat(a, b, FS, max_tau_s=L / 200.0, n_seg=5)
    if tap_calibrate:                                            # one-tap commissioning measures v itself
        e_tap = rng.normal(0, np.hypot(sync_sigma_ms * 1e-3, 0.5 / FS))
        v_use = dsp.wave_speed_from_tap(L, L / v + e_tap)
    else:
        v_use = v_assumed if v_assumed is not None else v
    return x, dsp.locate(tau, L, v_use), ratio


def stats(errs):
    errs = np.abs(np.asarray(errs))
    return dict(rms=float(np.sqrt(np.mean(errs ** 2))), median=float(np.median(errs)),
                p95=float(np.percentile(errs, 95)), within1=float(np.mean(errs <= 1.0) * 100), n=int(len(errs)))


def run(n, seed, **kw):
    rng = np.random.default_rng(seed)
    errs, xs = [], []
    for _ in range(n):
        x, xe, _r = one_trial(rng, **kw)
        errs.append(xe - x); xs.append(x)
    return np.array(xs), np.array(errs)


def main(n=250):
    res = {}
    # E1 error vs SNR (L = 8 m rig segment, 10 s record, 5 x 2 s averaged)
    snrs = [-35, -30, -25, -20, -15, -10, 0, 10]
    res["snr"] = {}
    for s in snrs:
        _, e = run(n, 100 + s, snr_db=s)
        res["snr"][s] = stats(e); print("SNR", s, res["snr"][s])
    # E2 error vs sync residual
    syncs = [0.0, 0.1, 0.3, 0.5, 1.0, 2.0]
    res["sync"] = {}
    for sg in syncs:
        _, e = run(n, 200, snr_db=5, sync_sigma_ms=sg)
        res["sync"][sg] = stats(e); print("sync", sg, res["sync"][sg])
    # E3 one-tap commissioning vs fixed datasheet speed, field segment L = 40 m, true v varies by pipe material
    rng = np.random.default_rng(300)
    xs, e_fixed, e_tap, vt = [], [], [], []
    for _ in range(n):
        v_true = rng.uniform(280, 450)
        x, xe, _ = one_trial(rng, L=40.0, v=v_true, snr_db=12, atten_len=60.0, v_assumed=400.0)
        x2, xe2, _ = one_trial(rng, L=40.0, v=v_true, x=x, snr_db=12, atten_len=60.0, tap_calibrate=True)
        xs.append(x); e_fixed.append(xe - x); e_tap.append(xe2 - x2); vt.append(v_true)
    res["tap"] = {"fixed_400": stats(e_fixed), "one_tap": stats(e_tap)}
    print("tap", res["tap"])
    # E4 quantisation (bandwidth saving for the pair link)
    res["bits"] = {}
    for b in [16, 8, 4, 1]:
        _, e = run(n, 400, snr_db=-17, sync_sigma_ms=0.1, bits=b)
        res["bits"][b] = stats(e); print("bits", b, res["bits"][b])
    json.dump(res, open(os.path.join(OUT, "..", "simulation_results.json"), "w"), indent=1)

    # ---- figures
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
    ax[0].plot(snrs, [res["snr"][s]["rms"] for s in snrs], "o-", color=BLUE)
    ax[0].axhline(1.0, color=RED, ls="--", lw=1); ax[0].text(snrs[0], 1.05, "±1 m design goal", color=RED, fontsize=8)
    ax[0].set_xlabel("per-node SNR at segment midpoint (dB)"); ax[0].set_ylabel("RMS location error (m)"); ax[0].set_yscale("log")
    ax[1].plot(snrs, [res["snr"][s]["within1"] for s in snrs], "o-", color=GREEN)
    ax[1].set_xlabel("per-node SNR at segment midpoint (dB)"); ax[1].set_ylabel("% of trials within ±1 m"); ax[1].set_ylim(0, 105)
    fig.suptitle("Simulated localisation, 8 m segment, 10 s record, 4 kHz, sync residual 0.3 ms", fontsize=10, color=NAVY)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "sim_snr.png"), dpi=170); plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    ax.plot(syncs, [res["sync"][s]["rms"] for s in syncs], "o-", color=BLUE, label="simulated RMS error")
    xx = np.linspace(0, 2, 50); ax.plot(xx, 400 * xx * 1e-3 / 2, "--", color=ORANGE, label="v·δt/2 (theory, 400 m/s)")
    ax.set_xlabel("sync residual σ between nodes (ms)"); ax.set_ylabel("RMS location error (m)"); ax.legend(frameon=False, fontsize=8)
    ax.set_title("Timing error sets the accuracy floor", fontsize=10, color=NAVY)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "sim_sync.png"), dpi=170); plt.close(fig)

    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    ax[0].scatter(xs, e_fixed, s=8, color=ORANGE, alpha=.7); ax[0].set_title(f"Datasheet v = 400 m/s fixed   (RMS {res['tap']['fixed_400']['rms']:.1f} m)", fontsize=9, color=NAVY)
    ax[1].scatter(xs, e_tap, s=8, color=GREEN, alpha=.7); ax[1].set_title(f"One-tap commissioning   (RMS {res['tap']['one_tap']['rms']:.2f} m)", fontsize=9, color=NAVY)
    for a_ in ax: a_.set_xlabel("true leak position from node A (m)"); a_.axhline(0, color="#888", lw=.8)
    ax[0].set_ylabel("location error (m)")
    fig.suptitle("40 m segment, mixed pipe materials (true v 280–450 m/s)", fontsize=10, color=NAVY)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "sim_tap.png"), dpi=170); plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    bl = [16, 8, 4, 1]; ax.bar([str(b) for b in bl], [res["bits"][b]["within1"] for b in bl], color=[BLUE, BLUE, BLUE, ORANGE])
    ax.set_xlabel("bits per sample exchanged between the pair"); ax.set_ylabel("% of trials within ±1 m"); ax.set_ylim(0, 105)
    ax.set_title("Compression of the pair link (SNR −17 dB)", fontsize=10, color=NAVY)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "sim_bits.png"), dpi=170); plt.close(fig)
    return res


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 250)
