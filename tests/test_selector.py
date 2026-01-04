import pytest

from agent.selector.selector import Selector
from agent.state.models import ActionVerb, IntentAction, IntentTarget, SafetyLevel, WorkingMemory


def test_selector_blocks_denied_terms():
    selector = Selector(deny_text={"purchase"})
    intent = IntentAction(verb=ActionVerb.CLICK, target=IntentTarget(name_contains="Purchase now"))
    with pytest.raises(ValueError):
        selector.gate(intent, WorkingMemory())


def test_selector_rate_limits_and_safety():
    selector = Selector(safety_level=SafetyLevel.HIGH, max_actions=1)
    safe_intent = IntentAction(verb=ActionVerb.CLICK)
    selector.gate(safe_intent, WorkingMemory(risk_mode="high"))
    with pytest.raises(ValueError):
        selector.gate(IntentAction(verb=ActionVerb.OPEN_URL), WorkingMemory())
