from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

from .config import Settings
from .dsp import stft_dbfs


def _to_image(arr: np.ndarray, width: int, height: int) -> Image.Image:
    arr = arr - np.min(arr)
    arr = arr / (np.max(arr) + 1e-9)
    arr = (arr * 255).astype(np.uint8)
    img = Image.fromarray(arr)
    return img.resize((width, height)).convert("L")


def generate_artifacts(samples: np.ndarray, event_id: str, settings: Settings, artifact_dir: Path) -> dict:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    wf = artifact_dir / f"{event_id}_waterfall.png"
    psd = artifact_dir / f"{event_id}_psd.png"
    if not settings.artifacts.enabled:
        return {"waterfall_thumb": None, "psd_thumb": None, "thumbnail_hash": None}
    try:
        _, _, db = stft_dbfs(samples, settings.rtl.sample_rate_sps, settings.capture.fft_size, settings.capture.fft_hop)
        wf_img = _to_image(np.flipud(db), settings.artifacts.width, settings.artifacts.height)
        wf_img.save(wf)
        psd_trace = np.mean(db, axis=1)[None, :]
        psd_img = _to_image(np.repeat(psd_trace, 64, axis=0), settings.artifacts.width, settings.artifacts.height)
        psd_img.save(psd)
        digest = hashlib.sha256(wf.read_bytes()).hexdigest()
        return {"waterfall_thumb": wf.name, "psd_thumb": psd.name, "thumbnail_hash": f"sha256:{digest}"}
    except Exception:
        return {"waterfall_thumb": None, "psd_thumb": None, "thumbnail_hash": None}
