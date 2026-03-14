from __future__ import annotations

import numpy as np

from .config import Settings
from .dsp import robust_noise_floor, stft_dbfs
from .heuristics import freq_behavior, spectral_shape, time_pattern


def _stats(values: list[float]) -> dict:
    if not values:
        return {"min": None, "median": None, "avg": None, "p95": None, "max": None, "std": None}
    arr = np.array(values)
    return {
        "min": float(np.min(arr)),
        "median": float(np.median(arr)),
        "avg": float(np.mean(arr)),
        "p95": float(np.percentile(arr, 95)),
        "max": float(np.max(arr)),
        "std": float(np.std(arr)),
    }


def extract_features(samples: np.ndarray, settings: Settings) -> dict:
    f, t, dbfs = stft_dbfs(samples, settings.rtl.sample_rate_sps, settings.capture.fft_size, settings.capture.fft_hop, settings.capture.window_type)
    noise_median, noise_p20 = robust_noise_floor(dbfs)
    active_mask = dbfs > noise_median + settings.detection.psd_active_threshold_db
    frame_active = np.any(active_mask, axis=0)
    active_idx = np.where(frame_active)[0]
    freqs = np.fft.fftshift(np.fft.fftfreq(settings.capture.fft_size, 1 / settings.rtl.sample_rate_sps)) / 1e6 + settings.rtl.center_freq_mhz

    dom_freqs, frame_power, bw = [], [], []
    for idx in active_idx:
        col = dbfs[:, idx]
        a = active_mask[:, idx]
        if not np.any(a):
            continue
        peak = int(np.argmax(col * a))
        dom_freqs.append(float(freqs[peak]))
        frame_power.append(float(np.max(col)))
        bins = np.where(a)[0]
        bw.append(float((bins.max() - bins.min() + 1) * settings.rtl.sample_rate_sps / settings.capture.fft_size / 1e3))

    burst_onsets, burst_durations = [], []
    ms_per_frame = settings.capture.fft_hop / settings.rtl.sample_rate_sps * 1000
    in_burst = False
    start = 0
    for i, a in enumerate(frame_active):
        if a and not in_burst:
            start = i
            in_burst = True
        elif not a and in_burst:
            end = i
            in_burst = False
            burst_onsets.append(start * ms_per_frame)
            burst_durations.append((end - start) * ms_per_frame)
    if in_burst:
        burst_onsets.append(start * ms_per_frame)
        burst_durations.append((len(frame_active) - start) * ms_per_frame)

    fb = freq_behavior(dom_freqs, (active_idx * ms_per_frame / 1000.0).tolist())
    tp = time_pattern(float(np.mean(frame_active) * 100), burst_onsets)
    ss = spectral_shape(float(np.median(bw)) if bw else None, 0.0, 0.1, 0.2)
    overload = bool(np.mean(np.abs(samples) > 0.95) > 0.01 or (frame_power and np.mean(np.array(frame_power) > -1) > 0.1))
    snr = float(np.median(frame_power) - noise_median) if frame_power else 0.0

    conf_base = min(1.0, len(active_idx) / 20.0)
    if abs(noise_median - noise_p20) > 6:
        conf_base *= 0.9
    if overload:
        conf_base *= 0.7

    return {
        "noise_floor_dbfs": noise_median,
        "snr_db": snr,
        "overload_detected": overload,
        "dominant_freqs": dom_freqs,
        "occupied_bw_khz": bw,
        "frame_power_dbfs": frame_power,
        "burst_onsets_ms": burst_onsets,
        "burst_durations_ms": burst_durations,
        "freq_behavior": fb,
        "time_pattern": tp,
        "spectral_shape": ss,
        "duty_cycle_pct": float(np.mean(frame_active) * 100),
        "burst_count": len(burst_durations),
        "dominant_freq_stats": {
            "min": min(dom_freqs) if dom_freqs else None,
            "median": float(np.median(dom_freqs)) if dom_freqs else None,
            "avg": float(np.mean(dom_freqs)) if dom_freqs else None,
            "max": max(dom_freqs) if dom_freqs else None,
            "std_khz": float(np.std(dom_freqs) * 1e3) if dom_freqs else None,
        },
        "occupied_bw_stats": _stats(bw),
        "power_stats": {
            "peak": float(np.max(frame_power)) if frame_power else None,
            "avg": float(np.mean(frame_power)) if frame_power else None,
            "median": float(np.median(frame_power)) if frame_power else None,
            "std": float(np.std(frame_power)) if frame_power else None,
        },
        "burst_ms_stats": _stats(burst_durations),
        "burst_spacing_stats": _stats(np.diff(burst_onsets).tolist() if len(burst_onsets) > 1 else []),
        "feature_confidence": {
            "dominant_freq": conf_base,
            "bandwidth": conf_base,
            "burst_timing": conf_base if len(burst_durations) >= 1 else 0.1,
            "freq_stability": conf_base,
            "shape_labels": conf_base,
        },
    }
