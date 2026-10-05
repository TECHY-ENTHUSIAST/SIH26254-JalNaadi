import numpy as np
from jalnaadi import dsp

FS = 4000
N = FS * 4


def test_pump_hum_is_tonal():
    t = np.arange(N) / FS
    x = sum(np.sin(2 * np.pi * 50 * h * t) / h for h in range(1, 6)) + 0.05 * np.random.default_rng(1).standard_normal(N)
    assert dsp.classify(dsp.features(x, FS), rms_floor=0.1) == "pump"


def test_broadband_hiss_is_leak():
    x = dsp.bandpass(np.random.default_rng(2).standard_normal(N), FS, 150, 600)
    assert dsp.classify(dsp.features(x / np.std(x), FS), rms_floor=0.1) == "leak"


def test_knock_is_tap():
    x = np.random.default_rng(3).standard_normal(N) * 0.05
    x[1000:1100] += 3 * np.hanning(100)
    assert dsp.classify(dsp.features(x, FS), rms_floor=0.1) == "tap"


def test_silence_is_quiet():
    x = np.random.default_rng(4).standard_normal(N) * 0.03
    assert dsp.classify(dsp.features(x, FS), rms_floor=0.1) == "quiet"
