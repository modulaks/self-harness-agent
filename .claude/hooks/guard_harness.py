#!/usr/bin/env python3
"""PreToolUse hook. Blokuje edycję plików chronionych (walidator, regresja, harness.yaml, hooki),
chyba że w katalogu projektu istnieje plik .harness_unlock (tworzy go człowiek).
Exit 2 = blokada, komunikat ze stderr trafia do Claude."""
import json
import os
import re
import sys

PROTECTED = [
    r"harness/harness\.yaml$",
    r"eval/regression/tasks\.jsonl$",
    r"eval/verifiers\.py$",
    r"eval/run_regression\.py$",
    r"learning/validator\.py$",
    r"learning/promote\.py$",
    r"\.claude/hooks/",
    r"\.claude/settings\.json$",
]
BASH_MUTATORS = r"(>|>>|\btee\b|\bsed\s+-i|\brm\b|\bmv\b|\bcp\b|\btruncate\b|\bpython[3]?\s+-c)"


def is_protected(path: str) -> bool:
    p = path.replace("\\", "/")
    return any(re.search(pat, p) for pat in PROTECTED)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    if os.path.exists(os.path.join(root, ".harness_unlock")):
        return 0
    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {}) or {}
    hit = None
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        fp = inp.get("file_path") or inp.get("notebook_path") or ""
        if is_protected(fp):
            hit = fp
    elif tool == "Bash":
        cmd = inp.get("command", "")
        if re.search(BASH_MUTATORS, cmd):
            for pat in PROTECTED:
                m = re.search(pat.replace("$", "").replace("\\.", "."), cmd)
                if m:
                    hit = cmd[:120]
                    break
    if hit:
        sys.stderr.write(
            f"[guard] Zablokowano modyfikację chronionego pliku: {hit}\n"
            "Agent nie może zmieniać walidatora, zestawu regresyjnego, harness.yaml ani hooków. "
            "Opisz proponowaną zmianę i jej powód; człowiek może utworzyć .harness_unlock. "
            "Kandydatów na harness zapisuj w harness/candidates/, nowe zadania w eval/regression/proposed_tasks.jsonl.\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
