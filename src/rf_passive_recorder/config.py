from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = "rf-passive-recorder"
    data_dir: str = "./data"
    log_level: str = "INFO"


class RTLConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_index: int = 0
    sample_rate_sps: int = 2048000
    center_freq_mhz: float = 915.2
    gain_mode: str = "manual"
    gain_db: float = 38.6
    agc_enabled: bool = False
    ppm_correction: float = 0.0


class CaptureConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pre_trigger_ms: int = 5000
    post_trigger_ms: int = 5000
    chunk_size: int = 262144
    ring_buffer_ms: int = 15000
    fft_size: int = 2048
    fft_hop: int = 512
    window_type: str = "hann"


class DetectionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    psd_active_threshold_db: float = 8.0
    min_burst_ms: float = 4.0
    merge_gap_ms: float = 8.0
    min_snr_db: float = 3.0


class ClusteringConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    distance_threshold: float = 0.18
    max_exemplars: int = 200


class ArtifactConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    width: int = 512
    height: int = 256


class GPIOConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    button_bcm_pin: int = 17
    debounce_ms: int = 300


class APIConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8787
    auth_token: str | None = None


class ExportConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    mode: str = "filesystem"
    outbox_dir: str | None = None
    http_url: str | None = None
    http_timeout_sec: float = 10.0
    http_auth_header: str | None = None
    retry_backoff_sec: int = 30


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    app: AppConfig = Field(default_factory=AppConfig)
    rtl: RTLConfig = Field(default_factory=RTLConfig)
    capture: CaptureConfig = Field(default_factory=CaptureConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    clustering: ClusteringConfig = Field(default_factory=ClusteringConfig)
    artifacts: ArtifactConfig = Field(default_factory=ArtifactConfig)
    gpio: GPIOConfig = Field(default_factory=GPIOConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)


def load_settings(path: str | None = None) -> Settings:
    cfg_path = Path(path) if path else Path("/etc/rf-passive-recorder/settings.yaml")
    if not cfg_path.exists():
        return Settings()
    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    settings = Settings.model_validate(data)
    if not settings.export.outbox_dir:
        settings.export.outbox_dir = str(Path(settings.app.data_dir) / "outbox")
    return settings
