#!/usr/bin/env python3
"""SessionStart hook: wypisuje stan projektu, stdout trafia do kontekstu Claude Code."""
import glob
import json
import os
import sqlite3

root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
lines = ["[stan projektu self-harness-agent]"]
try:
    import yaml
    with open(os.path.join(root, "harness", "harness.yaml"), encoding="utf-8") as f:
        h = yaml.safe_load(f)
    lines.append(f"harness: v{h.get('version')} executor={h.get('executor', {}).get('name')} critic={h.get('critic', {}).get('name')}")
except Exception as e:
    lines.append(f"harness: nie odczytano ({e})")
db = os.path.join(root, "data", "events.sqlite")
if os.path.exists(db):
    try:
        c = sqlite3.connect(db)
        n = c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        ends = c.execute("SELECT COUNT(*) FROM events WHERE kind='task_end'").fetchone()[0]
        fails = c.execute("SELECT COUNT(*) FROM events WHERE kind='task_end' AND payload LIKE '%\"ok\": false%'").fetchone()[0]
        lines.append(f"event log: {n} zdarzeń, {ends} epizodów, {fails} porażek")
    except Exception as e:
        lines.append(f"event log: błąd ({e})")
else:
    lines.append("event log: brak (jeszcze nic nie uruchomiono)")
cands = sorted(glob.glob(os.path.join(root, "harness", "candidates", "*.yaml")))
lines.append(f"kandydaci harnessu: {len(cands)}" + (f", ostatni: {os.path.basename(cands[-1])}" if cands else ""))
vals = sorted(glob.glob(os.path.join(root, "data", "validations", "*.json")))
if vals:
    try:
        r = json.load(open(vals[-1], encoding="utf-8"))
        lines.append(f"ostatnia walidacja: {os.path.basename(vals[-1])} accepted={r.get('accepted')} base={r.get('base_pass_rate')} cand={r.get('candidate_pass_rate')}")
    except Exception:
        pass
lines.append("STOP: " + ("AKTYWNY" if os.path.exists(os.path.join(root, "data", "STOP")) else "brak"))
lines.append("unlock: " + ("AKTYWNY (.harness_unlock)" if os.path.exists(os.path.join(root, ".harness_unlock")) else "brak, pliki chronione"))
lines.append("Bieżący kamień milowy: sprawdź ROADMAP.md")
print("\n".join(lines))
