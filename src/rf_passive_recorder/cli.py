from __future__ import annotations

import json
import threading
from pathlib import Path

import numpy as np
import typer
import uvicorn

from .api import create_api
from .config import load_settings
from .logging_setup import setup_logging
from .service import RecorderService
from .synthetic import generate_signal

app = typer.Typer(help="rf-passive-recorder CLI")


@app.command("run")
def run(config: str | None = typer.Option(None, "--config"), api_only: bool = False):
    settings = load_settings(config)
    setup_logging(settings.app.log_level, Path(settings.app.data_dir) / "logs" / "recorder.log")
    service = RecorderService(settings)
    if api_only:
        uvicorn.run(create_api(service), host=settings.api.host, port=settings.api.port)
    else:
        if settings.api.enabled:
            threading.Thread(
                target=uvicorn.run,
                args=(create_api(service),),
                kwargs={"host": settings.api.host, "port": settings.api.port},
                daemon=True,
            ).start()
        service.run()


@app.command("trigger")
def trigger(config: str | None = typer.Option(None, "--config")):
    settings = load_settings(config)
    service = RecorderService(settings)
    payload = service.process_trigger()
    typer.echo(payload["event_id"])


@app.command("replay")
def replay(input: Path = typer.Option(..., "--input"), config: str | None = typer.Option(None, "--config")):
    settings = load_settings(config)
    service = RecorderService(settings)
    data = np.fromfile(input, dtype=np.complex64)
    payload = service.process_trigger(synthetic_samples=data)
    typer.echo(json.dumps(payload, indent=2))


@app.command("inspect-event")
def inspect_event(event_id: str, config: str | None = typer.Option(None, "--config")):
    settings = load_settings(config)
    p = Path(settings.app.data_dir) / "events" / f"{event_id}.json"
    typer.echo(p.read_text(encoding="utf-8"))


@app.command("inspect-cluster")
def inspect_cluster(cluster_id: str, config: str | None = typer.Option(None, "--config")):
    settings = load_settings(config)
    p = Path(settings.app.data_dir) / "clusters" / f"{cluster_id}.json"
    typer.echo(p.read_text(encoding="utf-8"))


@app.command("export-pending")
def export_pending(config: str | None = typer.Option(None, "--config")):
    settings = load_settings(config)
    pending = Path(settings.app.data_dir) / "outbox" / "pending"
    typer.echo("\n".join(str(p) for p in pending.glob("*.json")))


@app.command("test-synthetic")
def test_synthetic(config: str | None = typer.Option(None, "--config")):
    settings = load_settings(config)
    service = RecorderService(settings)
    samples = generate_signal(settings.rtl.sample_rate_sps, 2.0, [120000], burst_period_s=0.2)
    payload = service.process_trigger(synthetic_samples=samples)
    typer.echo(json.dumps(payload, indent=2))


@app.command("init-db")
def init_db(config: str | None = typer.Option(None, "--config")):
    settings = load_settings(config)
    RecorderService(settings).storage.init_db()
    typer.echo("db initialized")


@app.command("print-config")
def print_config(config: str | None = typer.Option(None, "--config")):
    settings = load_settings(config)
    typer.echo(settings.model_dump_json(indent=2))


if __name__ == "__main__":
    app()
