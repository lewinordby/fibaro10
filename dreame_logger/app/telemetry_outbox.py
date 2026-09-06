from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4


class TelemetryOutbox:
    """Persist observations before delivery; never skip ahead of a failed batch."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._writer_lock = threading.Lock()
        self._delivery_lock = threading.Lock()
        self._sequence = 0

    def append(self, payload: dict[str, Any]) -> None:
        with self._writer_lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            self._sequence = max(time.time_ns(), self._sequence + 1)
            target = self.directory / f"{self._sequence:020d}-{uuid4().hex}.json"
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            temporary.replace(target)

    def count(self) -> int:
        return sum(1 for _ in self.directory.glob("*.json"))

    def flush(self, send: Callable[[dict[str, Any]], Any]) -> int:
        # Network I/O must not block the robot's property-change callbacks.
        with self._delivery_lock:
            sent = 0
            for path in sorted(self.directory.glob("*.json")):
                send(json.loads(path.read_text(encoding="utf-8")))
                path.unlink()
                sent += 1
            return sent
