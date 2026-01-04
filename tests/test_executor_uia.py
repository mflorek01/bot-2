from agent.executor.uia_executor import UIAExecutor
from agent.state.models import ActionVerb, ExecutionStatus, GroundedTarget, IntentAction, TargetSource, UIElement


class DummyWrapper:
    def __init__(self):
        self.clicked = False

    def click_input(self):
        self.clicked = True


def test_uia_executor_uses_backend_handle():
    wrapper = DummyWrapper()
    element = UIElement(
        element_id="id1",
        source=TargetSource.UIA,
        role="button",
        name="Ok",
        value=None,
        automation_id=None,
        class_name=None,
        bbox=None,
        states=[],
        parent_element_ids=[],
        near_text=None,
        salience=1.0,
        backend_ref=None,
    )
    intent = IntentAction(verb=ActionVerb.CLICK)
    target = GroundedTarget(element=element, confidence=1.0, alternatives=[])
    executor = UIAExecutor(app_loader=lambda _: wrapper)
    result = executor.execute(intent, target)
    assert result.status == ExecutionStatus.OK
    assert wrapper.clicked
