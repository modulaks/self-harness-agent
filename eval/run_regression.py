"""Uruchamia zestaw regresyjny na wskazanym harnessie i zapisuje raport.
python -m eval.run_regression [--harness PATH] [--tasks PATH] [--out PATH] [--ids a,b,c]"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from agent.config import EVENT_LOG_PATH, HARNESS_PATH, ROOT
from agent.event_log import EventLog
from agent.graph import finish_task, run_task
from agent.tools import reset_sandbox
from eval.verifiers import verify
from harness.schema import Harness, load_harness

TASKS_PATH = ROOT / "eval" / "regression" / "tasks.jsonl"


def load_tasks(path: Path = TASKS_PATH) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def run_regression(harness: Harness, log: EventLog, tasks: list[dict]) -> dict:
    results = []
    for task in tasks:
        reset_sandbox()
        for f in task.get("setup_files", []):
            p = ROOT / "sandbox" / f["path"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f["content"], encoding="utf-8")
        t0 = time.time()
        try:
            r = run_task(harness, log, task["prompt"], task_id=task["id"])
            ok, reason = verify(task, r)
        except Exception as e:  # błąd wykonania to porażka zadania, nie crash runnera
            r = {"run_id": "error", "answer": "", "steps": 0, "hit_max_steps": False}
            ok, reason = False, f"exception: {type(e).__name__}: {e}"
        if r["run_id"] != "error":
            finish_task(log, harness, r, ok, reason, task["id"])
        results.append({"id": task["id"], "ok": ok, "reason": reason, "run_id": r["run_id"],
                        "steps": r["steps"], "protected": bool(task.get("protected")), "seconds": round(time.time() - t0, 1)})
    n = len(results)
    passed = sum(r["ok"] for r in results)
    return {"harness_version": harness.version, "n": n, "passed": passed,
            "pass_rate": round(passed / n, 4) if n else 0.0, "ts": time.time(), "results": results}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--harness", default=str(HARNESS_PATH))
    ap.add_argument("--tasks", default=str(TASKS_PATH))
    ap.add_argument("--out", default=None)
    ap.add_argument("--ids", default=None, help="podzbiór zadań, po przecinku")
    a = ap.parse_args()
    harness = load_harness(a.harness)
    tasks = load_tasks(Path(a.tasks))
    if a.ids:
        keep = set(a.ids.split(","))
        tasks = [t for t in tasks if t["id"] in keep]
    log = EventLog(EVENT_LOG_PATH)
    rep = run_regression(harness, log, tasks)
    for r in rep["results"]:
        print(f"{'OK ' if r['ok'] else 'FAIL'} {r['id']:<28} kroki={r['steps']:<3} {r['reason']}")
    print(f"\nharness {rep['harness_version']}: {rep['passed']}/{rep['n']} pass_rate={rep['pass_rate']}")
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"raport: {a.out}")
    return 0 if rep["passed"] == rep["n"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
