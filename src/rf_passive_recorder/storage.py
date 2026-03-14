from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import EventRow


class Storage:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.db_path = data_dir / "db" / "recorder.sqlite3"

    def ensure_dirs(self) -> None:
        for p in ["db", "events", "clusters", "artifacts", "outbox/pending", "outbox/sent", "outbox/failed", "logs", "replay", "tmp"]:
            (self.data_dir / p).mkdir(parents=True, exist_ok=True)

    def connect(self):
        self.ensure_dirs()
        return sqlite3.connect(self.db_path)

    def init_db(self) -> None:
        with self.connect() as con:
            cur = con.cursor()
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    time_utc TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    sensor_id TEXT NOT NULL,
                    center_freq_mhz REAL NOT NULL,
                    sample_rate_sps INTEGER NOT NULL,
                    observation_window_ms INTEGER NOT NULL,
                    dominant_freq_mhz REAL,
                    occupied_bw_avg_khz REAL,
                    peak_power_dbfs REAL,
                    avg_power_dbfs REAL,
                    burst_count INTEGER,
                    duty_cycle_pct REAL,
                    spectral_shape TEXT,
                    time_pattern TEXT,
                    cluster_id TEXT,
                    event_json_path TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS event_artifacts (event_id TEXT, artifact_type TEXT, path TEXT);
                CREATE TABLE IF NOT EXISTS clusters (
                    cluster_id TEXT PRIMARY KEY,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    event_count INTEGER NOT NULL,
                    consensus_score REAL NOT NULL,
                    cluster_json_path TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cluster_membership (
                    event_id TEXT NOT NULL,
                    cluster_id TEXT NOT NULL,
                    distance_score REAL NOT NULL,
                    assigned_at_utc TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS exports (
                    export_id TEXT PRIMARY KEY,
                    object_type TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    last_attempt_utc TEXT,
                    error_text TEXT
                );
                """
            )
            con.commit()

    def write_event_json(self, event_id: str, payload: dict) -> Path:
        path = self.data_dir / "events" / f"{event_id}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def write_cluster_json(self, cluster_id: str, payload: dict) -> Path:
        path = self.data_dir / "clusters" / f"{cluster_id}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def insert_event(self, row: EventRow) -> None:
        with self.connect() as con:
            con.execute(
                """INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                tuple(row.model_dump().values()),
            )
            con.commit()

    def upsert_cluster(self, cluster_id: str, created_at: str, updated_at: str, event_count: int, consensus: float, path: str) -> None:
        with self.connect() as con:
            con.execute(
                """INSERT INTO clusters VALUES (?,?,?,?,?,?)
                ON CONFLICT(cluster_id) DO UPDATE SET updated_at_utc=excluded.updated_at_utc,event_count=excluded.event_count,consensus_score=excluded.consensus_score,cluster_json_path=excluded.cluster_json_path""",
                (cluster_id, created_at, updated_at, event_count, consensus, path),
            )
            con.commit()

    def add_membership(self, event_id: str, cluster_id: str, distance_score: float, assigned_at_utc: str) -> None:
        with self.connect() as con:
            con.execute("INSERT INTO cluster_membership VALUES (?,?,?,?)", (event_id, cluster_id, distance_score, assigned_at_utc))
            con.commit()

    def latest_events(self, limit: int = 20) -> list[dict]:
        with self.connect() as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("SELECT * FROM events ORDER BY time_utc DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_event(self, event_id: str) -> dict | None:
        with self.connect() as con:
            con.row_factory = sqlite3.Row
            r = con.execute("SELECT * FROM events WHERE event_id=?", (event_id,)).fetchone()
            return dict(r) if r else None
