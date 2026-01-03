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

* **Runtime dependencies:** Python 3.11+, `pywinauto` (UIA), `pyautogui` (mouse/keyboard fallback), and optional OCR/screenshot providers.
* **Run:** Create a small driver (e.g., `run_agent.py`) that instantiates `AutomationAgent`, sets `agent.memory.goal`, and calls `agent.run()`.
* **Observation/Execution:** `observer/observer.py` walks the UIA tree (Windows) into raw nodes; `executor/uia_executor.py` refinds elements via UIA and performs invoke/click/setvalue with mouse fallback in `executor/mouse_keyboard.py`.
* **Compression:** `perception/compression.py` converts UIA/OCR data into stable `UIElement`s, filters to interactive controls, and generates screen signatures for stuck detection.
* **Logging:** JSONL per run (`logs/<run_id>.jsonl`) with step-by-step events for replay/debugging.
* Vision support is reserved for future work via extension points in perception and grounding.

## Quickstart: Run on Windows and set objectives

1) Install dependencies (Python 3.11+):
```bash
pip install pywinauto pyautogui pillow
```
Add OCR/screenshot tools if desired (e.g., `pytesseract`, `opencv-python`, `mss`).

2) Verify your display/permissions:
- Run from an interactive Windows session (UIA requires desktop access).
- If using `pyautogui`, ensure the process is allowed to send input.

3) Set your objective and run:
- Edit `run_agent.py` and set `agent.memory.goal` to your high-level objective string.
- (Optional) Set `agent.memory.subgoal` or `agent.memory.constraints` for extra guidance.
- From the repo root:
```bash
python run_agent.py
```

4) What happens:
- The agent loop observes the foreground window via UIA, compresses to `UIState`, decides (procedure/micropolicy/LLM hooks), safety-gates, grounds targets, executes (UIA first, mouse/keyboard fallback), re-observes, and verifies (stuck/unchanged UI detection).
- Logs are written to `logs/<run_id>.jsonl` for replay/debugging.

5) Customizing inputs:
- Provide your own screenshot/OCR hooks when constructing `AutomationAgent(observer=Observer(...))`.
- Add trusted procedures in `SkillLibrary` to run deterministic flows for known apps.
- Integrate your LLM in `decision/llm_interface.py` for propose/rank behavior.
