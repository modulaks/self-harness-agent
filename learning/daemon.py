"""Pętla ucząca. --once: jeden cykl. Bez flagi: long-running z wyzwalaczem i kill switchem data/STOP.
Cykl: mining -> (poziom 1: pamięć | poziom 2: kandydat -> walidacja) -> czeka na zgodę człowieka."""
from __future__ import annotations

import argparse
import json
import time

from agent.config import EVENT_LOG_PATH, HARNESS_PATH, ROOT
from agent.event_log import EventLog
from harness.schema import load_harness
from learning.proposer import propose_harness, propose_memory
from learning.validator import validate
from learning.weakness_mining import mine

STATE_PATH = ROOT / "data" / "daemon_state.json"
STOP_PATH = ROOT / "data" / "STOP"


def _load_state() -> dict:
    return json.loads(STATE_PATH.read_text()) if STATE_PATH.is_file() else {"last_seen_id": 0, "cycles": 0}


def _save_state(s: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(s, indent=2))


def run_cycle(min_delta: float = 0.0) -> dict:
    harness = load_harness(HARNESS_PATH)
    log = EventLog(EVENT_LOG_PATH)
    state = _load_state()
    summary = {"cycle": state["cycles"] + 1, "clusters": 0, "memory_writes": [], "candidates": [], "validations": []}
    clusters = mine(harness, log, since_id=state["last_seen_id"])
    summary["clusters"] = len(clusters)
    for c in sorted(clusters, key=lambda c: -len(c.get("evidence", []))):
        if c["level"] == 1:
            summary["memory_writes"].append(str(propose_memory(harness, c, log)))
        elif c["level"] == 2:
            out = propose_harness(harness, c, log)
            if out:
                ypath, _ = out
                summary["candidates"].append(str(ypath))
                rep = validate(ypath, min_delta=min_delta, log=log)
                summary["validations"].append({"candidate": str(ypath), "accepted": rep.get("accepted"),
                                               "base": rep.get("base_pass_rate"), "cand": rep.get("candidate_pass_rate")})
                break  # jeden kandydat na cykl, resztę w kolejnym
        else:
            summary.setdefault("level3", []).append(c.get("pattern"))
    state["last_seen_id"] = log.last_id()
    state["cycles"] += 1
    state["last_cycle_ts"] = time.time()
    _save_state(state)
    log.append("daemon", harness.version, "cycle", summary)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=600, help="sekundy między sprawdzeniami")
    ap.add_argument("--min-new", type=int, default=5, help="min. nowych epizodów task_end do uruchomienia cyklu")
    ap.add_argument("--min-delta", type=float, default=0.0)
    a = ap.parse_args()
    if a.once:
        print(json.dumps(run_cycle(a.min_delta), ensure_ascii=False, indent=2))
        return
    print("daemon start, STOP: touch data/STOP")
    while not STOP_PATH.exists():
        state = _load_state()
        log = EventLog(EVENT_LOG_PATH)
        new_eps = len(log.by_kind("task_end", since_id=state["last_seen_id"]))
        log.close()
        if new_eps >= a.min_new:
            s = run_cycle(a.min_delta)
            print(time.strftime("%H:%M:%S"), json.dumps(s, ensure_ascii=False))
        time.sleep(a.interval)
    print("STOP wykryty, koniec")


if __name__ == "__main__":
    main()
