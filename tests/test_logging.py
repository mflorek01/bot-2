import json

from agent.logging.json_logger import LOG_VERSION, JsonLogger


def test_json_logger_emits_version(tmp_path):
    logger = JsonLogger(tmp_path, host_platform="test")
    logger.log(0, "observe", {"sample": True})
    path = tmp_path / f"{logger.run_id}.jsonl"
    with path.open() as f:
        payload = json.loads(f.readline())
    assert payload["version"] == LOG_VERSION
    assert payload["host_platform"] == "test"
