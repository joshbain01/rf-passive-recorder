from __future__ import annotations

import numpy as np


def generate_signal(sample_rate: int, seconds: float, freqs_hz: list[float], burst_period_s: float = 0.25, burst_width_s: float = 0.02, jitter_s: float = 0.0, drift_hz_per_s: float = 0.0, noise: float = 0.05) -> np.ndarray:
    n = int(sample_rate * seconds)
    t = np.arange(n) / sample_rate
    x = np.zeros(n, dtype=np.complex64)
    gate = np.zeros(n, dtype=float)
    cur = 0.0
    rng = np.random.default_rng(42)
    while cur < seconds:
        start = cur + (rng.normal(0, jitter_s) if jitter_s else 0)
        stop = start + burst_width_s
        i0, i1 = max(0, int(start * sample_rate)), min(n, int(stop * sample_rate))
        gate[i0:i1] = 1.0
        cur += burst_period_s
    for f in freqs_hz:
        phase = 2 * np.pi * (f * t + 0.5 * drift_hz_per_s * t * t)
        x += np.exp(1j * phase).astype(np.complex64)
    x *= gate
    x += (rng.normal(0, noise, n) + 1j * rng.normal(0, noise, n)).astype(np.complex64)
    x /= max(np.max(np.abs(x)), 1.0)
    return x.astype(np.complex64)
