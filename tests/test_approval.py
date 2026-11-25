"""The safety property that matters: a mis-heard 'approve' cannot act."""
from core.approval import ApprovalGate, needs_approval


def test_high_risk_is_held():
    assert needs_approval("pay vendor $5000", "high") is True
    assert needs_approval("transfer funds", "low") is True  # pattern match
    assert needs_approval("summarize the inbox", "low") is False


def test_vague_confirmation_rejected():
    g = ApprovalGate()
    p = g.hold("finance", "pay invoice A-2231 $5000", "high")
    for vague in ["approve", "yes", "ok", "do it", "go ahead"]:
        ok, _ = g.confirm(vague)
        assert ok is False, f"{vague!r} must not release the action"
    assert g.pending()[0].action_id == p.action_id  # still pending


def test_exact_id_releases():
    g = ApprovalGate()
    p = g.hold("finance", "pay invoice A-2231 $5000", "high")
    ok, aid = g.confirm(f"APPROVE {p.action_id}")
    assert ok is True and aid == p.action_id
    assert g.pending() == []


def test_wrong_id_does_not_release():
    g = ApprovalGate()
    g.hold("finance", "pay", "high")
    ok, _ = g.confirm("APPROVE ACT-dead")
    assert ok is False
