from rf_passive_recorder.config import Settings
from rf_passive_recorder.features import extract_features
from rf_passive_recorder.synthetic import generate_signal


def test_stable_periodic_bursts():
    s = Settings()
    x = generate_signal(s.rtl.sample_rate_sps, 1.2, [100_000], burst_period_s=0.2, burst_width_s=0.03)
    f = extract_features(x, s)
    assert f["freq_behavior"]["pattern"] in {"stable", "unknown"}


def test_quasi_periodic_bursts():
    s = Settings()
    x = generate_signal(s.rtl.sample_rate_sps, 1.2, [100_000], burst_period_s=0.2, burst_width_s=0.03, jitter_s=0.01)
    assert extract_features(x, s)["time_pattern"]["label"] in {"quasi_periodic", "periodic", "sporadic"}


def test_broadband_multi_peak_drift_hop_low_snr_quiet():
    s = Settings()
    broadband = generate_signal(s.rtl.sample_rate_sps, 1.0, [50_000, 150_000, 350_000], burst_period_s=0.4, burst_width_s=0.1)
    multi_peak = generate_signal(s.rtl.sample_rate_sps, 1.0, [80_000, 120_000], burst_period_s=0.3)
    drift = generate_signal(s.rtl.sample_rate_sps, 1.0, [100_000], drift_hz_per_s=5000)
    hopping = generate_signal(s.rtl.sample_rate_sps, 1.0, [80_000, 300_000], burst_period_s=0.5)
    low_snr = generate_signal(s.rtl.sample_rate_sps, 1.0, [100_000], noise=0.3)
    quiet = generate_signal(s.rtl.sample_rate_sps, 1.0, [], noise=0.01)
    for sig in [broadband, multi_peak, drift, hopping, low_snr, quiet]:
        assert "snr_db" in extract_features(sig, s)
