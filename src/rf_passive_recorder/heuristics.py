from __future__ import annotations

import numpy as np


def freq_behavior(freqs_mhz: list[float], frame_times_s: list[float]) -> dict:
    if len(freqs_mhz) < 2:
        return {"pattern": "unknown", "hop_count": 0, "hop_span_khz": 0.0, "channel_step_khz": 0.0}
    arr = np.array(freqs_mhz)
    std_khz = np.std(arr) * 1e3
    slope = np.polyfit(np.array(frame_times_s), arr * 1e3, 1)[0] if len(frame_times_s) >= 2 else 0.0
    rounded = np.round(arr * 1e3 / 25) * 25
    states, counts = np.unique(rounded, return_counts=True)
    persistent = states[counts >= 2]
    hop_count = max(0, len(persistent) - 1)
    hop_span = float((persistent.max() - persistent.min()) if len(persistent) else 0.0)
    channel_step = float(np.median(np.diff(np.sort(persistent))) if len(persistent) > 1 else 0.0)
    if hop_count == 0 and std_khz <= 10 and abs(slope) <= 2:
        pattern = "stable"
    elif hop_count == 0 and abs(slope) > 2:
        pattern = "drifting"
    elif hop_count >= 1 and hop_span >= 25:
        pattern = "hopping"
    else:
        pattern = "unknown"
    return {"pattern": pattern, "hop_count": int(hop_count), "hop_span_khz": hop_span, "channel_step_khz": channel_step}


def time_pattern(duty_cycle_pct: float, burst_onsets_ms: list[float]) -> dict:
    burst_count = len(burst_onsets_ms)
    if duty_cycle_pct >= 80 and burst_count <= 1:
        return {"label": "continuous", "periodicity_score": 1.0, "onset_style": "abrupt", "offset_style": "abrupt"}
    if burst_count < 2:
        return {"label": "unknown" if burst_count == 0 else "sporadic", "periodicity_score": 0.0, "onset_style": "abrupt", "offset_style": "abrupt"}
    spacing = np.diff(np.array(burst_onsets_ms))
    cv = float(np.std(spacing) / (np.mean(spacing) + 1e-9))
    score = float(max(0.0, min(1.0, 1.0 - min(cv, 1.0))))
    if burst_count >= 3 and cv < 0.05:
        label = "periodic"
    elif burst_count >= 3 and cv < 0.20:
        label = "quasi_periodic"
    else:
        label = "sporadic"
    return {"label": label, "periodicity_score": score, "onset_style": "abrupt", "offset_style": "abrupt"}


def spectral_shape(median_bw_khz: float | None, multi_peak_ratio: float, sideband_ratio: float, flatness: float) -> dict:
    if median_bw_khz is None:
        label = "unknown"
    elif median_bw_khz >= 1000:
        label = "broadband"
    elif multi_peak_ratio >= 0.5:
        label = "multi_peak"
    elif sideband_ratio >= 0.2:
        label = "sidebanded"
    elif median_bw_khz < 250:
        label = "single_narrowband_peak"
    else:
        label = "irregular"
    return {"label": label, "symmetry_score": float(max(0, 1 - sideband_ratio)), "sideband_score": float(sideband_ratio), "flatness": float(flatness)}
