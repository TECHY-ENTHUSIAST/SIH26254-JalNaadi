import numpy as np
from jalnaadi import dsp

FS = 4000


def _pair(x, L=8.0, v=400.0, seed=0):
    rng = np.random.default_rng(seed)
    s = dsp.bandpass(rng.standard_normal(FS * 6), FS)
    return dsp.fractional_delay(s, x / v, FS), dsp.fractional_delay(s, (L - x) / v, FS)


def test_localisation_noise_free():
    a, b = _pair(2.0)
    tau, ratio = dsp.gcc_phat(a, b, FS, 8 / 200.0)
    assert abs(dsp.locate(tau, 8.0, 400.0) - 2.0) < 0.01
    assert ratio > 20


def test_leak_at_centre_gives_zero_tau():
    a, b = _pair(4.0)
    tau, _ = dsp.gcc_phat(a, b, FS, 8 / 200.0)
    assert abs(tau) < 1e-4


def test_one_tap_wave_speed():
    assert abs(dsp.wave_speed_from_tap(8.0, 0.02) - 400.0) < 1e-9


def test_worked_example_from_master_document():
    # A-B 20 m, leak 6 m from A, v = 400 m/s -> tau = 20 ms -> x = 6 m
    tau = (14 - 6) / 400.0
    assert abs(dsp.locate(tau, 20.0, 400.0) - 6.0) < 1e-9


def test_sync_error_maps_to_position_error():
    a, b = _pair(2.0)
    b = dsp.fractional_delay(b, 0.001, FS)          # 1 ms residual
    tau, _ = dsp.gcc_phat(a, b, FS, 8 / 200.0)
    err = abs(dsp.locate(tau, 8.0, 400.0) - 2.0)
    assert abs(err - 400 * 0.001 / 2) < 0.03       # v*dt/2 = 0.2 m
