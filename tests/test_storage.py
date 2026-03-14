from pathlib import Path

from rf_passive_recorder.models import EventRow
from rf_passive_recorder.storage import Storage


def test_storage_init_and_insert(tmp_path: Path):
    st = Storage(tmp_path)
    st.init_db()
    row = EventRow(
        event_id="evt_1",
        time_utc="2026-01-01T00:00:00Z",
        created_at_utc="2026-01-01T00:00:01Z",
        sensor_id="sensor",
        center_freq_mhz=915.2,
        sample_rate_sps=2048000,
        observation_window_ms=10000,
        event_json_path="/tmp/e.json",
    )
    st.insert_event(row)
    assert st.get_event("evt_1") is not None
