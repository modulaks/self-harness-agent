"""Weakness mining: z porażek w event logu buduje klastry wg mechanizmu przyczynowego.
Wynik: lista {pattern, mechanism, level (1|2|3), evidence: [run_id], suggested_fix}."""
from __future__ import annotations

import json

from agent.event_log import EventLog
from harness.schema import Harness
from learning.common import ask_critic, parse_json

SYSTEM = """Jesteś krytykiem analizującym ślady wykonania agenta LLM. Grupujesz porażki według
MECHANIZMU PRZYCZYNOWEGO, nie objawu (dwa timeouty mogą mieć różne przyczyny).
Dla każdego klastra określ poziom naprawy:
1 = luka wiedzy lub procedury (do pamięci/skilli agenta),
2 = wada harnessu (prompt systemowy, zestaw narzędzi, polityki),
3 = systematyczna słabość modelu (nie do naprawienia promptem).
Odpowiadasz WYŁĄCZNIE JSON: lista obiektów z polami
pattern, mechanism, level, evidence (lista run_id), suggested_fix."""


def trajectory_digest(log: EventLog, run_id: str, max_chars: int = 2500) -> str:
    lines = []
    for e in log.run_events(run_id):
        p = e["payload"]
        k = e["kind"]
        if k == "task_start":
            lines.append(f"TASK: {p.get('prompt', '')[:300]}")
        elif k == "tool_call":
            lines.append(f"CALL {p['name']} {json.dumps(p['args'], ensure_ascii=False)[:200]}")
        elif k == "tool_result":
            lines.append(f"RESULT {str(p.get('content', ''))[:200]}")
        elif k == "llm_call" and not p["response"].get("tool_calls"):
            lines.append(f"SAY {p['response']['content'][:300]}")
        elif k == "task_end":
            lines.append(f"END ok={p['ok']} reason={p.get('verifier_reason')} steps={p['steps']}")
    return "\n".join(lines)[:max_chars]


def collect_failures(log: EventLog, since_id: int = 0, limit: int = 30) -> list[dict]:
    ends = [e for e in log.by_kind("task_end", since_id=since_id, limit=5000) if not e["payload"].get("ok")]
    ends = ends[-limit:]
    return [{"run_id": e["run_id"], "task_id": e["payload"].get("task_id"),
             "harness_version": e["harness_version"], "digest": trajectory_digest(log, e["run_id"])} for e in ends]


def mine(harness: Harness, log: EventLog, since_id: int = 0) -> list[dict]:
    failures = collect_failures(log, since_id)
    if not failures:
        return []
    dossier = "\n\n---\n\n".join(f"run_id={f['run_id']} task={f['task_id']}\n{f['digest']}" for f in failures)
    raw = ask_critic(harness, SYSTEM, f"Porażki ({len(failures)}):\n\n{dossier}\n\nZwróć JSON.")
    clusters = parse_json(raw)
    if not isinstance(clusters, list):
        log.append("mining", harness.version, "mining", {"error": "niesparsowana odpowiedź krytyka", "raw": raw[:2000]})
        return []
    valid_ids = {f["run_id"] for f in failures}
    for c in clusters:
        c["evidence"] = [r for r in c.get("evidence", []) if r in valid_ids]
        c["level"] = int(c.get("level", 2))
    log.append("mining", harness.version, "mining", {"n_failures": len(failures), "clusters": clusters})
    return clusters
