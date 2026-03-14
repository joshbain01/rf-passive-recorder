from rf_passive_recorder.heuristics import freq_behavior, spectral_shape, time_pattern


def test_freq_behavior_stable():
    fb = freq_behavior([915.2, 915.2001, 915.1999], [0.0, 0.1, 0.2])
    assert fb["pattern"] == "stable"


def test_time_pattern_quasi_periodic():
    tp = time_pattern(10.0, [0.0, 100.0, 205.0, 310.0])
    assert tp["label"] in {"quasi_periodic", "periodic"}


def test_spectral_shape_broadband():
    ss = spectral_shape(1200, 0.0, 0.1, 0.2)
    assert ss["label"] == "broadband"
