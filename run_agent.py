import argparse

from agent.agent_loop import AgentConfig, AutomationAgent
from agent.state.models import SafetyLevel


def main():
    args = _parse_args()
    config = AgentConfig(
        log_dir=args.log_dir,
        step_budget=args.step_budget,
        enable_ocr=not args.disable_ocr,
        enable_screenshots=not args.disable_screenshots,
        safety_level=SafetyLevel(args.safety_level),
        log_verbose=args.verbose,
        validate_dependencies=not args.skip_validation,
        ocr_binary=args.ocr_binary,
        llm_endpoint=args.llm_endpoint,
        llm_api_key=args.llm_api_key,
    )
    agent = AutomationAgent(config=config)
    agent.memory.goal = "Example goal: open an application window and click OK."
    agent.run()


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Windows automation agent.")
    parser.add_argument("--log-dir", default="logs", help="Directory to write logs and screenshots.")
    parser.add_argument("--step-budget", type=int, default=20, help="Maximum steps before stopping.")
    parser.add_argument("--disable-ocr", action="store_true", help="Disable OCR processing.")
    parser.add_argument("--disable-screenshots", action="store_true", help="Disable screenshot capture.")
    parser.add_argument(
        "--safety-level",
        choices=[level.value for level in SafetyLevel],
        default=SafetyLevel.NORMAL.value,
        help="Safety gating level for actions.",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--skip-validation", action="store_true", help="Skip dependency validation checks.")
    parser.add_argument("--ocr-binary", help="Path to tesseract executable for OCR.")
    parser.add_argument("--llm-endpoint", help="HTTP endpoint for LLM proposals.")
    parser.add_argument("--llm-api-key", help="API key for LLM endpoint.")
    return parser.parse_args()


if __name__ == "__main__":
    main()
