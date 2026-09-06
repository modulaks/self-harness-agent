"""Promocja kandydata do harness/harness.yaml. Wymaga raportu accepted=true
i zgody człowieka: pliku data/approvals/<nazwa_kandydata>.ok.
PLIK CHRONIONY: agent nie może go edytować (guard hook)."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from agent.config import EVENT_LOG_PATH, HARNESS_PATH, ROOT
from agent.event_log import EventLog
from harness.schema import bump_patch, load_harness, save_harness
from learning.validator import VALIDATIONS_DIR

APPROVALS_DIR = ROOT / "data" / "approvals"


def promote(candidate_path: Path, require_human: bool = True) -> str:
    cand = Path(candidate_path)
    report = VALIDATIONS_DIR / f"{cand.stem}.json"
    if not report.is_file():
        raise SystemExit(f"brak raportu walidacji: {report}")
    rep = json.loads(report.read_text(encoding="utf-8"))
    if not rep.get("accepted"):
        raise SystemExit("raport walidacji: accepted=false, promocja odrzucona")
    approval = APPROVALS_DIR / f"{cand.stem}.ok"
    if require_human and not approval.is_file():
        raise SystemExit(f"brak zgody człowieka, utwórz plik: {approval}")
    current = load_harness(HARNESS_PATH)
    new = load_harness(cand)
    new_version = bump_patch(current.version)
    new = new.model_copy(update={"version": new_version})
    backup = HARNESS_PATH.with_suffix(f".{current.version}.bak.yaml")
    shutil.copy(HARNESS_PATH, backup)
    save_harness(new, HARNESS_PATH)
    tag = f"harness-v{new_version}"
    try:
        subprocess.run(["git", "add", str(HARNESS_PATH), str(cand), str(cand.with_suffix('.md'))], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-m", f"promote harness {current.version} -> {new_version} ({cand.stem})"], cwd=ROOT, check=True)
        subprocess.run(["git", "tag", tag], cwd=ROOT, check=True)
    except Exception as e:  # git opcjonalny w M0-M2
        print(f"[git pominięty: {e}]")
    EventLog(EVENT_LOG_PATH).append("promote", new_version, "promotion",
                                    {"from": current.version, "to": new_version, "candidate": cand.stem, "report": str(report), "tag": tag})
    return new_version


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate")
    ap.add_argument("--no-human", action="store_true", help="tylko do testów")
    a = ap.parse_args()
    print("promowano do wersji", promote(Path(a.candidate), require_human=not a.no_human))
