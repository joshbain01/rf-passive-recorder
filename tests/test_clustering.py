from rf_passive_recorder.clustering import distance, feature_vector


def _payload(freq=915.2):
    return {
        "signal": {
            "dominant_freq_mhz": {"avg": freq, "std_khz": 2.0},
            "occupied_bw_khz": {"avg": 180.0, "std": 20.0},
            "power_dbfs": {"peak": -20.0, "avg": -35.0},
            "freq_behavior": {"pattern": "stable"},
        },
        "timing": {
            "duty_cycle_pct": 10.0,
            "burst_count": 6,
            "burst_ms": {"avg": 14.0, "std": 1.2},
            "burst_spacing_ms": {"avg": 220.0, "std": 8.0},
            "time_pattern": {"label": "quasi_periodic", "periodicity_score": 0.8},
        },
        "morphology": {"spectral_shape": {"label": "single_narrowband_peak"}},
    }


def test_distance_small_for_similar_payloads():
    a = feature_vector(_payload())
    b = feature_vector(_payload(915.201))
    c = feature_vector(_payload(918.0))
    assert distance(a, b) < distance(a, c)
