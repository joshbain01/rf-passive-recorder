from __future__ import annotations

from .config import load_settings
from .logging_setup import setup_logging
from .service import RecorderService


def run_daemon(config_path: str | None = None) -> None:
    settings = load_settings(config_path)
    setup_logging(settings.app.log_level)
    service = RecorderService(settings)
    service.run()
