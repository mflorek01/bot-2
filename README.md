# Windows Desktop Automation Agent

This repository implements a deterministic, Windows-first desktop automation agent architecture. The agent treats the language model as a proposal/verifier lens while deterministic modules handle observation, grounding, execution, and verification.

## Architecture

```
agent/
  observer/      # Collects UIA trees, screenshots, OCR text
  perception/    # Compresses observations into UIState with stable element IDs
  state/         # Shared schemas for intents, elements, memory, results
  skills/        # Procedures and grounding anchors with promotion/degradation rules
  decision/      # Micro-policies and LLM proposal/ranking entry points
  grounding/     # Resolves symbolic intents to concrete UI targets
  executor/      # UIA-first execution with mouse/keyboard fallback
  verifier/      # Closed-loop verification, stuck detection, guidance deltas
  selector/      # Safety gating for dangerous intents
  logging/       # Structured JSONL logging for replay/debugging
  agent_loop.py  # Control loop glue code
```

The high-level loop is:

1. Observe the active window (UIA snapshot, optional screenshot/OCR).
2. Compress to a `UIState` (interactive elements, stable IDs, salience).
3. Decide using procedures, micro-policy, or LLM proposer/verifier.
4. Safety gate and ground symbolic intent to a concrete target.
5. Execute (UIA preferred, mouse/keyboard fallback).
6. Re-observe and verify (focus, UI delta, stuck detection).
7. Update memory/skills and repeat.

## Development Notes

* Pywinauto-based observation/execution is stubbed for portability; integrate real calls in `observer/observer.py` and `executor/uia_executor.py`.
* UI compression, OCR, and screenshot capture are extensible hooks.
* Logging uses JSONL files per run (`logs/<run_id>.jsonl`) for replayability.
* Vision support is reserved for future work via extension points in perception and grounding.
