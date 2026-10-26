"""Writes the JSON-lines trace of a run. Traces hold prompts and tool output, so they stay local."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self


class Trace:
    """Appends one JSON object per line to a file, one line per event."""

    def __init__(self, path: Path, run_id: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self._file = path.open("a", encoding="utf-8")

    def write(self, event: str, **fields: Any) -> None:
        record = {
            "ts": datetime.now(UTC).isoformat(),
            "run_id": self.run_id,
            "event": event,
            **fields,
        }
        self._file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
