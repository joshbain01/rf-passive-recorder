from __future__ import annotations

import numpy as np
from scipy import signal


def stft_dbfs(samples: np.ndarray, sample_rate: int, fft_size: int, hop: int, window_type: str = "hann"):
    if len(samples) < fft_size:
        samples = np.pad(samples, (0, fft_size - len(samples)))
    win = signal.get_window(window_type, fft_size, fftbins=True)
    f, t, zxx = signal.stft(samples, fs=sample_rate, window=win, nperseg=fft_size, noverlap=fft_size - hop, boundary=None, padded=False)
    psd = np.abs(zxx) ** 2
    dbfs = 10.0 * np.log10(psd + 1e-12)
    return f, t, dbfs


def robust_noise_floor(dbfs: np.ndarray) -> tuple[float, float]:
    flat = dbfs.ravel()
    return float(np.median(flat)), float(np.percentile(flat, 20))
