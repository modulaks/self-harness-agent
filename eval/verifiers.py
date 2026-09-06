"""Weryfikatory zadań regresyjnych. Deterministyczne, bez LLM."""
from __future__ import annotations

import re

from agent.config import SANDBOX_DIR


def verify(task: dict, result: dict) -> tuple[bool, str]:
    v = task["verifier"]
    t = v["type"]
    answer = result.get("answer", "") or ""
    if t == "answer_contains":
        ok = v["value"].lower() in answer.lower()
        return ok, f"answer_contains '{v['value']}': {ok}"
    if t == "answer_regex":
        ok = re.search(v["value"], answer, re.I | re.S) is not None
        return ok, f"answer_regex /{v['value']}/: {ok}"
    if t == "file_exists":
        ok = (SANDBOX_DIR / v["path"]).is_file()
        return ok, f"file_exists {v['path']}: {ok}"
    if t == "file_contains":
        p = SANDBOX_DIR / v["path"]
        if not p.is_file():
            return False, f"file_contains {v['path']}: brak pliku"
        ok = v["value"] in p.read_text(encoding="utf-8", errors="replace")
        return ok, f"file_contains {v['path']} '{v['value']}': {ok}"
    return False, f"nieznany typ weryfikatora: {t}"
