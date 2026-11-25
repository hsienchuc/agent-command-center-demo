"""Append-only decision + activity logs (JSON lines)."""
from __future__ import annotations
import os, json, time, threading

LOG_DIR = os.environ.get("LOG_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs"))
os.makedirs(LOG_DIR, exist_ok=True)
_lock = threading.Lock()


def _append(fname: str, record: dict) -> dict:
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **record}
    with _lock:
        with open(os.path.join(LOG_DIR, fname), "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def activity(agent: str, event: str, detail: str = "") -> dict:
    return _append("activity_log.jsonl", {"agent": agent, "event": event, "detail": detail})


def decision(summary: str, actions: list, status: str) -> dict:
    return _append("decision_log.jsonl", {"summary": summary, "actions": actions, "status": status})


def tail(fname: str, n: int = 20) -> list[dict]:
    path = os.path.join(LOG_DIR, fname)
    if not os.path.exists(path):
        return []
    lines = open(path, encoding="utf-8").read().splitlines()[-n:]
    return [json.loads(x) for x in lines if x.strip()]
