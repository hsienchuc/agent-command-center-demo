"""Web command center: FastAPI backend + single-page UI.

Endpoints:
  GET  /            -> the command center UI
  GET  /state       -> agents, open handoffs, pending approvals, recent decisions, cost
  POST /message     -> {text} run a request through Adam
  POST /approve     -> {phrase} release a held action with  APPROVE <action_id>
  POST /reject      -> {action_id}
  POST /kill        -> engage the global kill switch
  POST /reset       -> clear the kill switch
"""
from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core import registry, supervisor, handoff, logstore, killswitch
from core.supervisor import GATE
from core import llm

HERE = os.path.dirname(__file__)
app = FastAPI(title="Multi-Agent Command Center (Demo)")


class Msg(BaseModel):
    text: str


class Phrase(BaseModel):
    phrase: str


class Aid(BaseModel):
    action_id: str


@app.get("/", response_class=HTMLResponse)
def index():
    return open(os.path.join(HERE, "static", "index.html"), encoding="utf-8").read()


@app.get("/state")
def state():
    agents = registry.load_agents()
    return JSONResponse({
        "kill": killswitch.engaged(),
        "agents": [{"name": a.name, "title": a.title, "risk": a.risk} for a in agents.values()],
        "open_handoffs": handoff.list_open(),
        "pending": [vars(p) for p in GATE.pending()],
        "decisions": logstore.tail("decision_log.jsonl", 8),
        "activity": logstore.tail("activity_log.jsonl", 12),
        "cost": llm.cost_snapshot(),
    })


@app.post("/message")
def message(m: Msg):
    try:
        return JSONResponse(supervisor.handle_request(m.text))
    except killswitch.KillSwitchEngaged as e:
        return JSONResponse({"error": str(e)}, status_code=423)


@app.post("/approve")
def approve(p: Phrase):
    ok, msg = GATE.confirm(p.phrase)
    if ok:
        logstore.activity("operator", "approved", msg)
    return {"ok": ok, "message": msg}


@app.post("/reject")
def reject(a: Aid):
    ok = GATE.reject(a.action_id)
    if ok:
        logstore.activity("operator", "rejected", a.action_id)
    return {"ok": ok}


@app.post("/kill")
def kill():
    killswitch.engage()
    logstore.activity("operator", "kill_switch", "engaged")
    return {"kill": True}


@app.post("/reset")
def reset():
    killswitch.reset()
    logstore.activity("operator", "kill_switch", "reset")
    return {"kill": False}
