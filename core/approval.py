"""Approval gate.

Why a mis-heard "approve" can't act:
  - Every held action gets a short random action_id (e.g. ACT-7f3a).
  - To release it the operator must provide the EXACT id: `APPROVE ACT-7f3a`.
  - Bare "approve" / "yes" / "ok" / "do it" (what a voice model mis-hears) is
    explicitly rejected. There is nothing to guess, so a wrong word fails safe.
  - Voice path: the UI only submits a confirmation when the recognised text
    contains the full id string; otherwise it asks the operator to repeat the id.
"""
from __future__ import annotations
import os, secrets, yaml, threading
from dataclasses import dataclass, field

CFG = os.environ.get("APPROVAL_RULES", os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "approval_rules.yaml"))


def _rules() -> dict:
    return yaml.safe_load(open(CFG, encoding="utf-8"))


def needs_approval(action_text: str, risk: str) -> bool:
    r = _rules()
    if risk in r.get("hold_risk", ["high"]):
        return True
    text = (action_text or "").lower()
    return any(p.lower() in text for p in r.get("high_risk_patterns", []))


@dataclass
class PendingAction:
    action_id: str
    agent: str
    action: str
    risk: str
    status: str = "pending"  # pending | approved | rejected


class ApprovalGate:
    def __init__(self):
        self._pending: dict[str, PendingAction] = {}
        self._lock = threading.Lock()

    def hold(self, agent: str, action: str, risk: str) -> PendingAction:
        aid = "ACT-" + secrets.token_hex(2)
        p = PendingAction(aid, agent, action, risk)
        with self._lock:
            self._pending[aid] = p
        return p

    def pending(self) -> list[PendingAction]:
        with self._lock:
            return [p for p in self._pending.values() if p.status == "pending"]

    def confirm(self, phrase: str) -> tuple[bool, str]:
        """Release an action ONLY on `APPROVE <exact action_id>`."""
        r = _rules()["confirmation"]
        text = (phrase or "").strip()
        low = text.lower()
        # Reject the vague words a voice model mis-hears.
        if low in [str(w).lower() for w in r.get("reject_vague", [])]:
            return False, "Vague confirmation rejected. Say: APPROVE <action id>."
        prefix = r.get("phrase_prefix", "APPROVE")
        if not low.startswith(prefix.lower()):
            return False, f"Confirmation must start with {prefix} and include the exact action id."
        with self._lock:
            for aid, p in self._pending.items():
                if p.status == "pending" and aid.lower() in low:
                    p.status = "approved"
                    return True, aid
        return False, "No pending action matched that exact id."

    def reject(self, action_id: str) -> bool:
        with self._lock:
            p = self._pending.get(action_id)
            if p and p.status == "pending":
                p.status = "rejected"
                return True
        return False
