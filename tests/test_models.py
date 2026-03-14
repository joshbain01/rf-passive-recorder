from rf_passive_recorder.models import ClusterPayload, EventPayload


def test_event_payload_model_accepts_minimal_shape():
    payload = {
        "schema_version": "1.0",
        "event_id": "evt_1",
        "time_utc": "2026-01-01T00:00:00Z",
        "sensor": {},
        "capture": {},
        "quality": {},
        "signal": {},
        "timing": {},
        "morphology": {},
        "artifacts": {},
        "provenance": {},
    }
    assert EventPayload.model_validate(payload).event_id == "evt_1"


def test_cluster_payload_model_accepts_shape():
    payload = {
        "schema_version": "1.0",
        "cluster_id": "cluster_1",
        "updated_utc": "2026-01-01T00:00:00Z",
        "event_count": 1,
        "consensus_score": 1.0,
        "stability": {},
        "consensus_features": {},
        "quality_summary": {},
        "representative_artifacts": {},
        "inference_context": {},
    }
    assert ClusterPayload.model_validate(payload).cluster_id == "cluster_1"
