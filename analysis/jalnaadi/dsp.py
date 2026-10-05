"""Signal-processing core of NAADI-EAR.

Conventions
-----------
Two clamp-on nodes A and B sit on one pipe segment of known length L (metres).
tau = t_B - t_A  (seconds) is the arrival-time difference of the leak noise.
Leak position measured from node A:   x = (L - v * tau) / 2
Wave speed from a commissioning tap:  v = L / dt_tap
"""
from __future__ import annotations
import numpy as np
from scipy import signal


def bandpass(x, fs, lo=50.0, hi=1000.0, order=4):
    sos = signal.butter(order, [lo, hi], btype="band", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x)


def fractional_delay(x, delay_s, fs):
    """Delay x by delay_s seconds (fractional or negative) using a frequency-domain phase shift."""
    n = len(x)
    nfft = int(2 ** np.ceil(np.log2(n + int(abs(delay_s) * fs) + 8)))
    X = np.fft.rfft(x, nfft)
    f = np.fft.rfftfreq(nfft, 1.0 / fs)
    y = np.fft.irfft(X * np.exp(-2j * np.pi * f * delay_s), nfft)
    return y[:n]


def gcc_phat(a, b, fs, max_tau_s, band=(50.0, 1000.0), n_seg=1):
    """Generalised cross-correlation with phase transform (GCC-PHAT).

    Returns (tau_s, peak_ratio). tau_s > 0 means b lags a (the leak is nearer to a).
    peak_ratio = peak / median(|cc|) is a confidence figure.
    Long records are split into n_seg segments whose correlation functions are averaged.
    """
    n = min(len(a), len(b))
    seg = n // n_seg
    nfft = int(2 ** np.ceil(np.log2(2 * seg)))
    f = np.fft.rfftfreq(nfft, 1.0 / fs)
    mask = (f >= band[0]) & (f <= band[1])
    acc = np.zeros(nfft)
    for s in range(n_seg):
        A = np.fft.rfft(a[s * seg:(s + 1) * seg], nfft)
        B = np.fft.rfft(b[s * seg:(s + 1) * seg], nfft)
        R = np.conj(A) * B
        R = np.where(mask, R / (np.abs(R) + 1e-12), 0.0)
        acc += np.fft.irfft(R, nfft)
    max_lag = int(np.ceil(max_tau_s * fs))
    cc = np.concatenate((acc[-max_lag:], acc[:max_lag + 1]))
    lags = np.arange(-max_lag, max_lag + 1)
    k = int(np.argmax(cc))
    frac = 0.0
    if 0 < k < len(cc) - 1:                      # parabolic interpolation -> sub-sample lag
        y0, y1, y2 = cc[k - 1], cc[k], cc[k + 1]
        den = y0 - 2 * y1 + y2
        if den != 0:
            frac = 0.5 * (y0 - y2) / den
    tau = (lags[k] + frac) / fs
    ratio = float(cc[k] / (np.median(np.abs(cc)) + 1e-12))
    return float(tau), ratio


def locate(tau_s, L_m, v_ms):
    """Leak distance from node A in metres."""
    return (L_m - v_ms * tau_s) / 2.0


def wave_speed_from_tap(L_m, dt_tap_s):
    """One-tap commissioning: tap beside node A, measure the A->B arrival gap."""
    return L_m / dt_tap_s


def quantise(x, bits):
    """Uniform quantisation to `bits` bits (1 bit = sign). Used to study bandwidth-saving options."""
    if bits >= 16:
        return x
    if bits == 1:
        return np.sign(x)
    scale = np.max(np.abs(x)) + 1e-12
    levels = 2 ** (bits - 1) - 1
    return np.round(x / scale * levels) / levels * scale


# ------------------------------------------------------------ on-node classifier
def features(x, fs, band=(50.0, 1000.0)):
    """Spectral features for the rule-based classifier (all cheap enough for an ESP32)."""
    f, p = signal.welch(x, fs=fs, nperseg=512)
    m = (f >= band[0]) & (f <= band[1])
    pb = p[m] + 1e-18
    flatness = float(np.exp(np.mean(np.log(pb))) / np.mean(pb))      # Wiener entropy, 0..1
    k = 8                                                             # local prominence of the strongest spectral line
    tonal = 1.0
    for i in range(len(pb)):
        nb = np.concatenate((pb[max(0, i - k):max(0, i - 2)], pb[i + 3:i + k + 1]))
        if len(nb) >= 4:
            tonal = max(tonal, float(pb[i] / np.median(nb)))
    band_ratio = float(np.sum(p[m]) / (np.sum(p) + 1e-18))           # in-band energy fraction
    xc = x - np.mean(x)
    s = np.std(xc) + 1e-18
    kurt = float(np.mean((xc / s) ** 4) - 3.0)                        # excess kurtosis
    rms = float(np.sqrt(np.mean(xc ** 2)))
    return dict(flatness=flatness, tonal=tonal, band_ratio=band_ratio, kurtosis=kurt, rms=rms)


def classify(feat, rms_floor=0.0, tonal_max=12.0, kurt_max=2.0, band_min=0.6):
    """Rule-based classifier -> 'leak' | 'pump' | 'tap' | 'quiet'."""
    if feat["rms"] <= rms_floor:
        return "quiet"
    if feat["kurtosis"] > kurt_max:
        return "tap"      # impulsive / bursty: draw-off or knock
    if feat["tonal"] > tonal_max:
        return "pump"     # narrow-band hum
    if feat["band_ratio"] >= band_min:
        return "leak"     # stationary broadband hiss
    return "quiet"
