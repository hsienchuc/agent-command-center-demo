"""Anthropic Claude calls + per-agent cost tracking."""
from __future__ import annotations
import os, json, threading
import anthropic

MODEL = os.environ.get("MODEL", "claude-sonnet-5-5")

# USD per million tokens. Override via PRICE_IN / PRICE_OUT env for other models.
PRICE_IN = float(os.environ.get("PRICE_IN", "3.0"))
PRICE_OUT = float(os.environ.get("PRICE_OUT", "15.0"))

_client = None
_lock = threading.Lock()
# cost ledger: {agent_name: {"calls": n, "in": tok, "out": tok, "usd": float}}
COST: dict[str, dict] = {}


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    return _client


def _track(agent: str, usage) -> None:
    with _lock:
        row = COST.setdefault(agent, {"calls": 0, "in": 0, "out": 0, "usd": 0.0})
        row["calls"] += 1
        row["in"] += usage.input_tokens
        row["out"] += usage.output_tokens
        row["usd"] += usage.input_tokens / 1e6 * PRICE_IN + usage.output_tokens / 1e6 * PRICE_OUT


def ask(agent: str, system_prompt: str, user_content: str, max_tokens: int = 700) -> str:
    """One Claude turn for `agent`. user_content is treated as DATA by the prompt."""
    resp = _get_client().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    _track(agent, resp.usage)
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def cost_snapshot() -> dict:
    with _lock:
        total = sum(r["usd"] for r in COST.values())
        return {"model": MODEL, "per_agent": json.loads(json.dumps(COST)), "total_usd": round(total, 4)}
