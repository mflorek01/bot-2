from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List


def load_events(path: Path) -> List[dict]:
    events: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def render(events: Iterable[dict]) -> None:
    for event in events:
        prefix = f"[{event.get('step_index'):02d}] {event.get('kind')}"
        payload = event.get("payload", {})
        print(f"{prefix:<18} {payload}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay agent run from JSONL log.")
    parser.add_argument("--log-dir", default="logs", help="Directory containing JSONL logs.")
    parser.add_argument("--run-id", help="Run identifier (hex). If omitted, the newest log is used.")
    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    if args.run_id:
        path = log_dir / f"{args.run_id}.jsonl"
    else:
        candidates = sorted(log_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            raise SystemExit("No logs found.")
        path = candidates[0]

    events = load_events(path)
    print(f"Loaded {len(events)} events from {path.name}")
    render(events)


if __name__ == "__main__":
    main()
