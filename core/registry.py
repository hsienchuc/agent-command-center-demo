"""Load agent definitions from markdown files (frontmatter + body)."""
from __future__ import annotations
import os, re
from dataclasses import dataclass, field

AGENTS_DIR = os.environ.get("AGENTS_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "agents"))


@dataclass
class Agent:
    name: str
    title: str
    risk: str
    system_prompt: str
    routes_to: list[str] = field(default_factory=list)


def _parse(path: str) -> Agent:
    raw = open(path, encoding="utf-8").read()
    meta: dict = {}
    body = raw
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if m:
        body = m.group(2).strip()
        for line in m.group(1).splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if v.startswith("[") and v.endswith("]"):
                meta[k] = [x.strip() for x in v[1:-1].split(",") if x.strip()]
            else:
                meta[k] = v
    name = meta.get("name") or os.path.splitext(os.path.basename(path))[0]
    return Agent(
        name=name,
        title=meta.get("title", name),
        risk=meta.get("risk", "low"),
        system_prompt=body,
        routes_to=meta.get("routes_to", []) if isinstance(meta.get("routes_to"), list) else [],
    )


def load_agents() -> dict[str, Agent]:
    """Return {name: Agent}. Swapping real agent files in needs no code change."""
    out: dict[str, Agent] = {}
    for fn in sorted(os.listdir(AGENTS_DIR)):
        if fn.endswith(".md"):
            a = _parse(os.path.join(AGENTS_DIR, fn))
            out[a.name] = a
    return out
