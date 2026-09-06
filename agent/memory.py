"""Poziom 1: pamięć proceduralna (skille) i faktograficzna. Minimalna wersja.
Docelowo: operatory assert/merge/invalidate/derive na event logu."""
from __future__ import annotations

import json
import time
from pathlib import Path

from agent.config import ROOT
from harness.schema import MemoryCfg


def load_skills_text(cfg: MemoryCfg, max_chars: int = 4000) -> str:
    d = ROOT / cfg.skills_dir
    if not cfg.inject_skills or not d.exists():
        return ""
    parts = []
    for f in sorted(d.glob("*.md")):
        parts.append(f"## {f.stem}\n{f.read_text(encoding='utf-8').strip()}")
    text = "\n\n".join(parts)
    return text[:max_chars]


def assert_fact(cfg: MemoryCfg, statement: str, source_run_id: str) -> None:
    p = ROOT / cfg.facts_file
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "op": "assert", "statement": statement, "source": source_run_id},
                           ensure_ascii=False) + "\n")


def write_skill(cfg: MemoryCfg, name: str, content: str) -> Path:
    d = ROOT / cfg.skills_dir
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.md"
    p.write_text(content.strip() + "\n", encoding="utf-8")
    return p
