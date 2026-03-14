from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StatsBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min: float | None = None
    median: float | None = None
    avg: float | None = None
    p95: float | None = None
    max: float | None = None
    std: float | None = None


class DominantFreqBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min: float | None = None
    median: float | None = None
    avg: float | None = None
    max: float | None = None
    std_khz: float | None = None


class EventPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = "1.0"
    event_id: str
    time_utc: str
    sensor: dict[str, Any]
    capture: dict[str, Any]
    quality: dict[str, Any]
    signal: dict[str, Any]
    timing: dict[str, Any]
    morphology: dict[str, Any]
    artifacts: dict[str, Any]
    provenance: dict[str, str]


class ClusterPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = "1.0"
    cluster_id: str
    updated_utc: str
    event_count: int
    consensus_score: float
    stability: dict[str, Any]
    consensus_features: dict[str, Any]
    quality_summary: dict[str, Any]
    representative_artifacts: dict[str, Any]
    inference_context: dict[str, Any]


class EventRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    time_utc: str
    created_at_utc: str
    sensor_id: str
    center_freq_mhz: float
    sample_rate_sps: int
    observation_window_ms: int
    dominant_freq_mhz: float | None = None
    occupied_bw_avg_khz: float | None = None
    peak_power_dbfs: float | None = None
    avg_power_dbfs: float | None = None
    burst_count: int = 0
    duty_cycle_pct: float = 0.0
    spectral_shape: str | None = None
    time_pattern: str | None = None
    cluster_id: str | None = None
    event_json_path: str
