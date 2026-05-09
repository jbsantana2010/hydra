from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_ROOT = Path(os.getenv("HYDRA_LOG_ROOT", "logs"))


def log_runtime_event(event_type: str, payload: dict) -> None:
    """Append a runtime event as one JSON line."""
    _append_jsonl(LOG_ROOT / "runtime" / "runtime_events.jsonl", event_type, payload)


def log_verification_event(event_type: str, payload: dict) -> None:
    """Append a verification event as one JSON line."""
    _append_jsonl(LOG_ROOT / "verification" / "verification_history.jsonl", event_type, payload)


def _append_jsonl(path: Path, event_type: str, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "payload": payload,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
