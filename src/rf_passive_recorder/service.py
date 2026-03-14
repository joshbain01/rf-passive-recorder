from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

import numpy as np

from .artifacts import generate_artifacts
from .clustering import distance, feature_vector, update_cluster_summary
from .config import Settings
from .exporter import Exporter
from .features import extract_features
from .models import ClusterPayload, EventPayload, EventRow
from .ring_buffer import ComplexRingBuffer
from .rtl_capture import RTLCapture
from .storage import Storage
from .trigger import TriggerManager
from .utils import utc_now_z

LOGGER = logging.getLogger(__name__)


class RecorderService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.storage = Storage(Path(settings.app.data_dir))
        self.storage.init_db()
        self.ring = ComplexRingBuffer(settings.rtl.sample_rate_sps, settings.capture.ring_buffer_ms)
        self.capture = RTLCapture(settings)
        self.trigger_manager = TriggerManager()
        self.trigger_manager.setup_gpio(settings.gpio.enabled, settings.gpio.button_bcm_pin, settings.gpio.debounce_ms)
        self.exporter = Exporter(settings, self.storage.data_dir, self.storage)
        self._event_counter = 0
        self._clusters: dict[str, dict] = {}

    def _next_event_id(self) -> str:
        self._event_counter += 1
        return f"evt_{self._event_counter:06d}"

    def run(self) -> None:
        self.capture.start()
        t = threading.Thread(target=self.capture.stream, args=(self.ring.append,), daemon=True)
        t.start()
        LOGGER.info("daemon started")
        while True:
            src = self.trigger_manager.wait_for_trigger(timeout=0.2)
            if not src:
                continue
            LOGGER.info("trigger received source=%s", src)
            threading.Thread(target=self.process_trigger, daemon=True).start()

    def process_trigger(self, synthetic_samples: np.ndarray | None = None) -> dict:
        event_id = self._next_event_id()
        trigger_time = utc_now_z()
        pre_n = int(self.settings.rtl.sample_rate_sps * self.settings.capture.pre_trigger_ms / 1000)
        post_n = int(self.settings.rtl.sample_rate_sps * self.settings.capture.post_trigger_ms / 1000)
        if synthetic_samples is None:
            pre, dropped = self.ring.snapshot_last(pre_n)
            post = self.capture.read_chunk()
            while len(post) < post_n:
                post = np.concatenate([post, self.capture.read_chunk()])
            post = post[:post_n]
            samples = np.concatenate([pre, post])
        else:
            samples = synthetic_samples.astype(np.complex64)
            dropped = False
        feat = extract_features(samples, self.settings)
        artifacts = generate_artifacts(samples, event_id, self.settings, self.storage.data_dir / "artifacts")
        payload = self._build_event_payload(event_id, trigger_time, feat, artifacts, dropped)
        EventPayload.model_validate(payload)
        epath = self.storage.write_event_json(event_id, payload)
        row = EventRow(
            event_id=event_id,
            time_utc=payload["time_utc"],
            created_at_utc=utc_now_z(),
            sensor_id=payload["sensor"]["id"],
            center_freq_mhz=payload["capture"]["center_freq_mhz"],
            sample_rate_sps=payload["capture"]["sample_rate_sps"],
            observation_window_ms=payload["capture"]["observation_window_ms"],
            dominant_freq_mhz=payload["signal"]["dominant_freq_mhz"]["avg"],
            occupied_bw_avg_khz=payload["signal"]["occupied_bw_khz"]["avg"],
            peak_power_dbfs=payload["signal"]["power_dbfs"]["peak"],
            avg_power_dbfs=payload["signal"]["power_dbfs"]["avg"],
            burst_count=payload["timing"]["burst_count"],
            duty_cycle_pct=payload["timing"]["duty_cycle_pct"],
            spectral_shape=payload["morphology"]["spectral_shape"]["label"],
            time_pattern=payload["timing"]["time_pattern"]["label"],
            cluster_id=None,
            event_json_path=str(epath),
        )
        cluster_id, dist, summary = self._cluster(payload)
        row.cluster_id = cluster_id
        self.storage.insert_event(row)
        self.storage.add_membership(event_id, cluster_id, dist, utc_now_z())
        cpath = self.storage.write_cluster_json(cluster_id, summary)
        self.storage.upsert_cluster(cluster_id, summary["updated_utc"], summary["updated_utc"], summary["event_count"], summary["consensus_score"], str(cpath))
        self.exporter.export_payload("event", event_id, payload)
        self.exporter.export_payload("cluster", cluster_id, summary)
        return payload

    def _cluster(self, payload: dict) -> tuple[str, float, dict]:
        if not self.settings.clustering.enabled:
            cluster_id = "cluster_000001"
            self._clusters.setdefault(cluster_id, {"vectors": [], "events": [], "distances": []})
        vec = feature_vector(payload)
        if not self._clusters:
            cluster_id = "cluster_000001"
            d = 0.0
        else:
            cand = []
            for cid, c in self._clusters.items():
                mean = np.mean(c["vectors"], axis=0)
                cand.append((cid, distance(vec, mean)))
            cluster_id, d = min(cand, key=lambda x: x[1])
            if d > self.settings.clustering.distance_threshold:
                cluster_id = f"cluster_{len(self._clusters)+1:06d}"
                d = 0.0
        cluster = self._clusters.setdefault(cluster_id, {"vectors": [], "events": [], "distances": []})
        cluster["vectors"].append(vec)
        cluster["events"].append(payload)
        cluster["distances"].append(d)
        summary = update_cluster_summary(cluster_id, cluster["events"], cluster["distances"])
        ClusterPayload.model_validate(summary)
        return cluster_id, d, summary

    def _build_event_payload(self, event_id: str, trigger_time: str, feat: dict, artifacts: dict, dropped: bool) -> dict:
        return {
            "schema_version": "1.0",
            "event_id": event_id,
            "time_utc": trigger_time,
            "sensor": {"id": "rf-passive-recorder-v1", "hardware": "rtl-sdr", "antenna_profile": "default", "ppm_correction": self.settings.rtl.ppm_correction},
            "capture": {
                "observation_window_ms": self.settings.capture.pre_trigger_ms + self.settings.capture.post_trigger_ms,
                "pre_trigger_ms": self.settings.capture.pre_trigger_ms,
                "post_trigger_ms": self.settings.capture.post_trigger_ms,
                "sample_rate_sps": self.settings.rtl.sample_rate_sps,
                "fft_size": self.settings.capture.fft_size,
                "center_freq_mhz": self.settings.rtl.center_freq_mhz,
                "scan_mode": "fixed_center",
                "gain_mode": self.settings.rtl.gain_mode,
                "gain_db": self.settings.rtl.gain_db,
                "agc_enabled": self.settings.rtl.agc_enabled,
            },
            "quality": {
                "noise_floor_dbfs": feat["noise_floor_dbfs"],
                "snr_db": feat["snr_db"],
                "overload_detected": feat["overload_detected"],
                "dropped_samples": dropped,
                "feature_confidence": feat["feature_confidence"],
            },
            "signal": {
                "dominant_freq_mhz": feat["dominant_freq_stats"],
                "freq_behavior": feat["freq_behavior"],
                "occupied_bw_khz": feat["occupied_bw_stats"],
                "power_dbfs": feat["power_stats"],
            },
            "timing": {
                "duty_cycle_pct": feat["duty_cycle_pct"],
                "burst_count": feat["burst_count"],
                "burst_ms": feat["burst_ms_stats"],
                "burst_spacing_ms": feat["burst_spacing_stats"],
                "time_pattern": feat["time_pattern"],
            },
            "morphology": {
                "spectral_shape": feat["spectral_shape"],
                "envelope_shape": {"label": "rectangular_burst", "rise_time_ms_avg": 0.8, "fall_time_ms_avg": 0.7},
            },
            "artifacts": artifacts,
            "provenance": {
                "dominant_freq_mhz": "measured",
                "occupied_bw_khz": "derived",
                "freq_behavior.pattern": "heuristic",
                "time_pattern.label": "heuristic",
                "spectral_shape.label": "heuristic",
            },
        }
