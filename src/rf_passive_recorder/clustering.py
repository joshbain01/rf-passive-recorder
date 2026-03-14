from __future__ import annotations

import math
from collections import Counter

import numpy as np

PATTERNS = ["stable", "drifting", "hopping", "unknown"]
TIME_LABELS = ["periodic", "quasi_periodic", "sporadic", "continuous", "unknown"]
SHAPE_LABELS = ["single_narrowband_peak", "multi_peak", "broadband", "sidebanded", "irregular", "unknown"]


def _one_hot(value: str, vocab: list[str]) -> list[float]:
    return [1.0 if value == v else 0.0 for v in vocab]


def feature_vector(payload: dict) -> np.ndarray:
    sig, tim, morph = payload["signal"], payload["timing"], payload["morphology"]
    vals = [
        sig["dominant_freq_mhz"].get("avg") or 0.0,
        sig["dominant_freq_mhz"].get("std_khz") or 0.0,
        sig["occupied_bw_khz"].get("avg") or 0.0,
        sig["occupied_bw_khz"].get("std") or 0.0,
        sig["power_dbfs"].get("peak") or -120.0,
        sig["power_dbfs"].get("avg") or -120.0,
        tim.get("duty_cycle_pct") or 0.0,
        float(tim.get("burst_count") or 0),
        tim["burst_ms"].get("avg") or 0.0,
        tim["burst_ms"].get("std") or 0.0,
        tim["burst_spacing_ms"].get("avg") or 0.0,
        tim["burst_spacing_ms"].get("std") or 0.0,
        tim["time_pattern"].get("periodicity_score") or 0.0,
    ]
    vals += _one_hot(sig["freq_behavior"]["pattern"], PATTERNS)
    vals += _one_hot(tim["time_pattern"]["label"], TIME_LABELS)
    vals += _one_hot(morph["spectral_shape"]["label"], SHAPE_LABELS)
    return np.array(vals, dtype=float)


def distance(a: np.ndarray, b: np.ndarray) -> float:
    scale = np.maximum(np.abs(b), 1.0)
    return float(np.sqrt(np.mean(((a - b) / scale) ** 2)))


def update_cluster_summary(cluster_id: str, members: list[dict], distances: list[float]) -> dict:
    ev_count = len(members)
    def arr(path, default=0.0):
        out=[]
        for p in members:
            cur=p
            for key in path:
                cur=cur.get(key,{}) if isinstance(cur,dict) else {}
            out.append(cur if isinstance(cur,(int,float)) else default)
        return np.array(out,dtype=float)
    shape_mode = Counter(m["morphology"]["spectral_shape"]["label"] for m in members)
    tp_mode = Counter(m["timing"]["time_pattern"]["label"] for m in members)
    consensus = max(0.0, min(1.0, 1.0 - float(np.mean(distances) if distances else 1.0)))
    exemplar_i = int(np.argmin(np.array(distances))) if distances else 0
    exemplar = members[exemplar_i]
    return {
        "schema_version": "1.0",
        "cluster_id": cluster_id,
        "updated_utc": members[-1]["time_utc"],
        "event_count": ev_count,
        "consensus_score": consensus,
        "stability": {
            "dominant_freq_mhz_std": float(np.std(arr(["signal", "dominant_freq_mhz", "avg"]))),
            "occupied_bw_khz_std": float(np.std(arr(["signal", "occupied_bw_khz", "avg"]))),
            "burst_ms_std": float(np.std(arr(["timing", "burst_ms", "avg"]))),
            "burst_spacing_ms_std": float(np.std(arr(["timing", "burst_spacing_ms", "avg"]))),
            "shape_label_consistency": shape_mode.most_common(1)[0][1] / ev_count,
            "time_pattern_consistency": tp_mode.most_common(1)[0][1] / ev_count,
        },
        "consensus_features": {
            "dominant_freq_mhz": float(np.mean(arr(["signal", "dominant_freq_mhz", "avg"]))),
            "occupied_bw_khz_avg": float(np.mean(arr(["signal", "occupied_bw_khz", "avg"]))),
            "duty_cycle_pct_avg": float(np.mean(arr(["timing", "duty_cycle_pct"]))),
            "burst_count_avg": float(np.mean(arr(["timing", "burst_count"]))),
            "burst_ms_avg": float(np.mean(arr(["timing", "burst_ms", "avg"]))),
            "burst_spacing_ms_avg": float(np.mean(arr(["timing", "burst_spacing_ms", "avg"]))),
            "freq_behavior_pattern": Counter(m["signal"]["freq_behavior"]["pattern"] for m in members).most_common(1)[0][0],
            "spectral_shape_label": shape_mode.most_common(1)[0][0],
            "time_pattern_label": tp_mode.most_common(1)[0][0],
        },
        "quality_summary": {
            "avg_snr_db": float(np.mean(arr(["quality", "snr_db"]))),
            "overload_rate": float(np.mean(arr(["quality", "overload_detected"]))),
            "dropped_sample_rate": float(np.mean(arr(["quality", "dropped_samples"]))),
        },
        "representative_artifacts": {
            "exemplar_event_id": exemplar["event_id"],
            "waterfall_thumb": exemplar["artifacts"].get("waterfall_thumb"),
            "psd_thumb": exemplar["artifacts"].get("psd_thumb"),
        },
        "inference_context": {"analysis_goal": "rank broad benign-source categories", "exact_device_identification": False},
    }
