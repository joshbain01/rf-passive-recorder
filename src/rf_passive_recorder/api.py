from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException


def create_api(service) -> FastAPI:
    app = FastAPI(title="rf-passive-recorder")

    def _auth(x_api_token: str | None):
        token = service.settings.api.auth_token
        if token and x_api_token != token:
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.get("/healthz")
    def healthz(x_api_token: str | None = Header(default=None)):
        _auth(x_api_token)
        return {"status": "ok", "name": service.settings.app.name}

    @app.post("/trigger")
    def trigger(x_api_token: str | None = Header(default=None)):
        _auth(x_api_token)
        service.trigger_manager.trigger("api")
        return {"triggered": True}

    @app.get("/events/latest")
    def events_latest(x_api_token: str | None = Header(default=None)):
        _auth(x_api_token)
        return service.storage.latest_events()

    @app.get("/events/{event_id}")
    def event(event_id: str, x_api_token: str | None = Header(default=None)):
        _auth(x_api_token)
        row = service.storage.get_event(event_id)
        if not row:
            raise HTTPException(status_code=404, detail="not found")
        return row

    @app.get("/clusters/{cluster_id}")
    def cluster(cluster_id: str, x_api_token: str | None = Header(default=None)):
        _auth(x_api_token)
        p = service.storage.data_dir / "clusters" / f"{cluster_id}.json"
        if not p.exists():
            raise HTTPException(status_code=404, detail="not found")
        return p.read_text(encoding="utf-8")

    return app
