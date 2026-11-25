"""Global kill switch — a flag file that halts all agent runs."""
from __future__ import annotations
import os

LOG_DIR = os.environ.get("LOG_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs"))
FLAG = os.path.join(LOG_DIR, "KILL")


def engaged() -> bool:
    return os.path.exists(FLAG)


def engage() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    open(FLAG, "w").write("stopped")


def reset() -> None:
    if os.path.exists(FLAG):
        os.remove(FLAG)


class KillSwitchEngaged(RuntimeError):
    pass


def guard() -> None:
    if engaged():
        raise KillSwitchEngaged("Kill switch engaged — all runs halted. Reset to resume.")
