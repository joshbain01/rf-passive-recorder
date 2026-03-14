from __future__ import annotations

import logging
import threading
from queue import Queue

LOGGER = logging.getLogger(__name__)

try:
    from gpiozero import Button
except Exception:  # pragma: no cover
    Button = None


class TriggerManager:
    def __init__(self):
        self.queue: Queue[str] = Queue()
        self._button = None

    def trigger(self, source: str = "software") -> None:
        self.queue.put(source)

    def setup_gpio(self, enabled: bool, pin: int, debounce_ms: int) -> None:
        if not enabled:
            return
        if Button is None:
            LOGGER.warning("GPIO support unavailable")
            return
        self._button = Button(pin=pin, pull_up=True, bounce_time=debounce_ms / 1000)
        self._button.when_pressed = lambda: self.trigger("gpio")

    def wait_for_trigger(self, timeout: float = 0.1) -> str | None:
        try:
            return self.queue.get(timeout=timeout)
        except Exception:
            return None
