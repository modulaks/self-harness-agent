"""Walidator: harness bieżący vs kandydat na tym samym zestawie regresyjnym.
Reguła: pass_rate(kandydat) >= pass_rate(bieżący) + min_delta i zero regresji na zadaniach protected.
PLIK CHRONIONY: agent nie może go edytować (guard hook)."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from agent.config import EVENT_LOG_PATH, HARNESS_PATH, ROOT
from agent.event_log import EventLog
from eval.run_regression import TASKS_PATH, load_tasks, run_regression
from harness.schema import load_harness, only_editable_changed

VALIDATIONS_DIR = ROOT / "data" / "validations"


def validate(candidate_path: Path, current_path: Path = HARNESS_PATH, tasks_path: Path = TASKS_PATH,
             min_delta: float = 0.0, log: EventLog | None = None) -> dict:
    current, cand = load_harness(current_path), load_harness(candidate_path)
    log = log or EventLog(EVENT_LOG_PATH)
    tasks = load_tasks(tasks_path)
    legal, illegal = only_editable_changed(current, cand)
    if not legal:
        rep = {"accepted": False, "reason": f"kandydat zmienia chronione pola: {illegal}", "candidate": str(candidate_path)}
        log.append("validator", current.version, "validation", rep)
        return rep
    base = run_regression(current, log, tasks)
    new = run_regression(cand, log, tasks)
    base_ok = {r["id"]: r["ok"] for r in base["results"]}
    regressions = [r["id"] for r in new["results"] if base_ok.get(r["id"]) and not r["ok"]]
    protected_regr = [r["id"] for r in new["results"] if r["protected"] and base_ok.get(r["id"]) and not r["ok"]]
    accepted = (new["pass_rate"] >= base["pass_rate"] + min_delta) and not protected_regr
    rep = {"accepted": accepted, "candidate": str(candidate_path), "current_version": current.version,
           "base_pass_rate": base["pass_rate"], "candidate_pass_rate": new["pass_rate"], "min_delta": min_delta,
           "regressions": regressions, "protected_regressions": protected_regr, "ts": time.time(),
           "base": base, "candidate_run": new}
    VALIDATIONS_DIR.mkdir(parents=True, exist_ok=True)
    out = VALIDATIONS_DIR / f"{Path(candidate_path).stem}.json"
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    rep["report_path"] = str(out)
    log.append("validator", current.version, "validation",
               {k: rep[k] for k in ("accepted", "candidate", "base_pass_rate", "candidate_pass_rate", "regressions", "protected_regressions")})
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate")
    ap.add_argument("--min-delta", type=float, default=0.0)
    a = ap.parse_args()
    r = validate(Path(a.candidate), min_delta=a.min_delta)
    print(json.dumps({k: v for k, v in r.items() if k not in ("base", "candidate_run")}, ensure_ascii=False, indent=2))
