from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

LOG_VERSION = 1


@dataclass
class LogEvent:
    run_id: str
    step_index: int
    kind: str
    payload: Dict[str, Any]
    timestamp: float
    version: int
    host_platform: Optional[str] = None


class JsonLogger:
    def __init__(self, log_dir: Path, host_platform: Optional[str] = None):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = uuid.uuid4().hex
        self.host_platform = host_platform

    def log(self, step_index: int, kind: str, payload: Dict[str, Any]) -> None:
        event = LogEvent(
            run_id=self.run_id,
            step_index=step_index,
            kind=kind,
            payload=payload,
            timestamp=time.time(),
            version=LOG_VERSION,
            host_platform=self.host_platform,
        )
        path = self.log_dir / f"{self.run_id}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
