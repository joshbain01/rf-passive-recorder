import logging

from rf_passive_recorder.config import Settings
from rf_passive_recorder.rtl_capture import RTLCapture


class FakeRtlSdr:
    def __init__(self, device_index: int):
        self.device_index = device_index
        self.sample_rate = None
        self.center_freq = None
        self._freq_correction = None
        self.gain = None

    @property
    def freq_correction(self):
        return self._freq_correction

    @freq_correction.setter
    def freq_correction(self, value):
        self._freq_correction = value


class FakeRtlSdrFailsFreqCorrection(FakeRtlSdr):
    @FakeRtlSdr.freq_correction.setter
    def freq_correction(self, value):
        raise RuntimeError("bad ppm")


def test_start_skips_setting_zero_ppm(monkeypatch):
    monkeypatch.setattr("rf_passive_recorder.rtl_capture.RtlSdr", FakeRtlSdr)
    settings = Settings.model_validate({"rtl": {"ppm_correction": 0}})

    capture = RTLCapture(settings)
    capture.start()

    assert capture.running is True
    assert capture.sdr.freq_correction is None


def test_start_logs_warning_when_freq_correction_fails(monkeypatch, caplog):
    monkeypatch.setattr("rf_passive_recorder.rtl_capture.RtlSdr", FakeRtlSdrFailsFreqCorrection)
    settings = Settings.model_validate({"rtl": {"ppm_correction": 1}})

    capture = RTLCapture(settings)
    with caplog.at_level(logging.WARNING):
        capture.start()

    assert capture.running is True
    assert "Failed to set RTL-SDR ppm correction" in caplog.text
