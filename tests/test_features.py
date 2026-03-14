from rf_passive_recorder.config import Settings
from rf_passive_recorder.features import extract_features
from rf_passive_recorder.synthetic import generate_signal


def test_extract_features_has_expected_blocks():
    s = Settings()
    x = generate_signal(s.rtl.sample_rate_sps, 1.0, [100_000], burst_period_s=0.15)
    f = extract_features(x, s)
    assert "noise_floor_dbfs" in f
    assert f["burst_count"] >= 1
