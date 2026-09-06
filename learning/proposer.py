"""Proposer: z klastra słabości generuje kandydata na harness (poziom 2)
albo wpis do pamięci (poziom 1). Kandydat zmienia tylko EDITABLE_FIELDS."""
from __future__ import annotations

import time
from pathlib import Path

import yaml

from agent.config import ROOT
from agent.event_log import EventLog
from agent.memory import write_skill
from harness.schema import EDITABLE_FIELDS, Harness, only_editable_changed, save_harness
from learning.common import ask_critic, parse_json

CANDIDATES_DIR = ROOT / "harness" / "candidates"

SYSTEM = """Proponujesz JEDNĄ minimalną zmianę harnessu agenta LLM, która usuwa opisaną słabość.
Możesz zmienić tylko pola: system_prompt, tools (spośród dostępnych), policies (max_steps, tool_timeout_s,
max_output_chars), memory. Nie dodawaj nowych narzędzi spoza listy dostępnych.
Odpowiadasz WYŁĄCZNIE JSON: {"changes": {<pole>: <nowa wartość>}, "rationale": "<uzasadnienie po polsku>"}.
W changes podajesz pełną nową wartość pola (np. cały nowy system_prompt)."""

AVAILABLE_TOOLS = ["list_dir", "read_file", "write_file", "run_python"]


def propose_harness(harness: Harness, cluster: dict, log: EventLog) -> tuple[Path, Path] | None:
    user = (f"Bieżący harness (YAML):\n{yaml.safe_dump(harness.model_dump(), allow_unicode=True, sort_keys=False)}\n"
            f"Dostępne narzędzia: {AVAILABLE_TOOLS}\n\nSłabość:\n{cluster}\n\nZwróć JSON.")
    raw = ask_critic(harness, SYSTEM, user)
    data = parse_json(raw)
    if not isinstance(data, dict) or "changes" not in data:
        log.append("proposer", harness.version, "proposal", {"error": "niesparsowana propozycja", "raw": raw[:2000]})
        return None
    changes = {k: v for k, v in data["changes"].items() if k in EDITABLE_FIELDS}
    if not changes:
        return None
    cand = harness.model_copy(update=changes)
    cand = Harness.model_validate({**cand.model_dump(), "version": f"{harness.version}-cand"})
    ok, illegal = only_editable_changed(harness, cand)
    if not ok:
        log.append("proposer", harness.version, "proposal", {"error": f"niedozwolone pola: {illegal}"})
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    ypath = CANDIDATES_DIR / f"{stamp}.yaml"
    mpath = CANDIDATES_DIR / f"{stamp}.md"
    save_harness(cand, ypath)
    mpath.write_text(
        f"# Kandydat {stamp}\n\nBazowy harness: {harness.version}\n\n## Słabość\n{cluster.get('pattern')}\n\n"
        f"Mechanizm: {cluster.get('mechanism')}\n\nDowody (run_id): {', '.join(cluster.get('evidence', []))}\n\n"
        f"## Zmienione pola\n{', '.join(changes)}\n\n## Uzasadnienie\n{data.get('rationale', '')}\n",
        encoding="utf-8")
    log.append("proposer", harness.version, "proposal",
               {"candidate": str(ypath.relative_to(ROOT)), "changed": list(changes), "evidence": cluster.get("evidence", [])})
    return ypath, mpath


def propose_memory(harness: Harness, cluster: dict, log: EventLog) -> Path:
    """Poziom 1: zapis skilla proceduralnego zamiast zmiany harnessu."""
    name = "skill-" + time.strftime("%Y%m%d-%H%M%S")
    content = (f"# {cluster.get('pattern')}\n\nMechanizm: {cluster.get('mechanism')}\n\n"
               f"Postępowanie: {cluster.get('suggested_fix')}\n\nŹródło: {', '.join(cluster.get('evidence', []))}")
    p = write_skill(harness.memory, name, content)
    log.append("proposer", harness.version, "proposal", {"memory_skill": str(p.relative_to(ROOT)), "evidence": cluster.get("evidence", [])})
    return p
