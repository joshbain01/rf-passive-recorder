from __future__ import annotations

import logging
import time
from collections.abc import Callable

import numpy as np

from .config import Settings

LOGGER = logging.getLogger(__name__)

try:
    from rtlsdr import RtlSdr
except Exception:  # pragma: no cover
    RtlSdr = None


class RTLCapture:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sdr = None
        self.running = False

    def start(self) -> None:
        if RtlSdr is None:
            LOGGER.warning("pyrtlsdr unavailable; using synthetic zero source")
            self.running = True
            return
        self.sdr = RtlSdr(self.settings.rtl.device_index)
        self.sdr.sample_rate = self.settings.rtl.sample_rate_sps
        self.sdr.center_freq = self.settings.rtl.center_freq_mhz * 1e6
        ppm_correction = int(self.settings.rtl.ppm_correction)
        if ppm_correction != 0:
            try:
                self.sdr.freq_correction = ppm_correction
            except Exception as exc:
                LOGGER.warning("Failed to set RTL-SDR ppm correction to %d: %s", ppm_correction, exc)
        self.sdr.gain = "auto" if self.settings.rtl.gain_mode == "auto" else self.settings.rtl.gain_db
        self.running = True
        LOGGER.info("RTL-SDR initialized")

    def stop(self) -> None:
        self.running = False
        if self.sdr:
            self.sdr.close()

    def read_chunk(self) -> np.ndarray:
        if not self.running:
            raise RuntimeError("capture not started")
        if self.sdr is None:
            return (np.random.randn(self.settings.capture.chunk_size) + 1j * np.random.randn(self.settings.capture.chunk_size)).astype(np.complex64) * 0.001
        return self.sdr.read_samples(self.settings.capture.chunk_size).astype(np.complex64)

    def stream(self, callback: Callable[[np.ndarray], None]) -> None:
        backoff = 1.0
        while self.running:
            try:
                callback(self.read_chunk())
                backoff = 1.0
            except Exception:
                LOGGER.exception("SDR read failure; retrying")
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)
