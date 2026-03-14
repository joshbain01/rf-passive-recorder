from __future__ import annotations

import json
import logging
import shutil
import time
import uuid
from pathlib import Path

import requests

from .config import Settings
from .utils import utc_now_z

LOGGER = logging.getLogger(__name__)


class Exporter:
    def __init__(self, settings: Settings, data_dir: Path, db):
        self.settings = settings
        self.data_dir = data_dir
        self.db = db

    def export_payload(self, object_type: str, object_id: str, payload: dict) -> None:
        if not self.settings.export.enabled:
            return
        mode = self.settings.export.mode
        if mode in {"filesystem", "both"}:
            pending = self.data_dir / "outbox" / "pending" / f"{object_type}_{object_id}.json"
            pending.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            self._record(object_type, object_id, "filesystem", "pending", None)
        if mode in {"http", "both"} and self.settings.export.http_url:
            self._send_http(object_type, object_id, payload)

    def _send_http(self, object_type: str, object_id: str, payload: dict) -> None:
        headers = {"Content-Type": "application/json"}
        if self.settings.export.http_auth_header:
            headers["Authorization"] = self.settings.export.http_auth_header
        try:
            resp = requests.post(self.settings.export.http_url, json=payload, headers=headers, timeout=self.settings.export.http_timeout_sec)
            resp.raise_for_status()
            self._record(object_type, object_id, "http", "sent", None)
        except Exception as e:
            LOGGER.exception("HTTP export failed")
            self._record(object_type, object_id, "http", "failed", str(e))
            time.sleep(min(self.settings.export.retry_backoff_sec, 1))

    def _record(self, object_type: str, object_id: str, mode: str, state: str, error: str | None) -> None:
        with self.db.connect() as con:
            con.execute(
                "INSERT INTO exports VALUES (?,?,?,?,?,?,?,?)",
                (f"exp_{uuid.uuid4().hex[:10]}", object_type, object_id, mode, state, 1, utc_now_z(), error),
            )
            con.commit()
