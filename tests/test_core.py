import json
import subprocess
import sys
from pathlib import Path

from agent.event_log import EventLog
from harness.schema import Harness, bump_patch, load_harness, only_editable_changed
from learning.common import parse_json

ROOT = Path(__file__).resolve().parent.parent


def test_event_log_append_only(tmp_path):
    log = EventLog(tmp_path / "e.sqlite")
    log.append("r1", "0.1.0", "task_start", {"prompt": "x"})
    log.append("r1", "0.1.0", "task_end", {"ok": False})
    assert log.count() == 2
    assert [e["kind"] for e in log.run_events("r1")] == ["task_start", "task_end"]
    assert log.by_kind("task_end")[0]["payload"]["ok"] is False
    assert not hasattr(log, "update") and not hasattr(log, "delete")


def test_harness_loads_and_editable_check():
    h = load_harness(ROOT / "harness" / "harness.yaml")
    assert h.tools and h.system_prompt
    cand = h.model_copy(update={"system_prompt": h.system_prompt + "\nX"})
    assert only_editable_changed(h, cand) == (True, [])
    bad = Harness.model_validate({**h.model_dump(), "critic": {"provider": "fake", "name": "x"}})
    ok, illegal = only_editable_changed(h, bad)
    assert not ok and illegal == ["critic"]
    assert bump_patch("0.1.9") == "0.1.10" and bump_patch("1.2.3-cand") == "1.2.4"


def test_parse_json_tolerates_fences_and_think():
    raw = "<think>hmm</think>Oto wynik:\n```json\n[{\"level\": 2, \"evidence\": []}]\n```"
    assert parse_json(raw) == [{"level": 2, "evidence": []}]
    assert parse_json("brak json") is None


def _guard(payload: dict, cwd: Path) -> int:
    p = subprocess.run([sys.executable, str(ROOT / ".claude/hooks/guard_harness.py")], input=json.dumps(payload),
                       text=True, capture_output=True, env={"CLAUDE_PROJECT_DIR": str(cwd)})
    return p.returncode


def test_guard_blocks_protected_and_respects_unlock(tmp_path):
    edit = {"tool_name": "Edit", "tool_input": {"file_path": str(tmp_path / "harness/harness.yaml")}}
    assert _guard(edit, tmp_path) == 2
    assert _guard({"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "harness/candidates/x.yaml")}}, tmp_path) == 0
    assert _guard({"tool_name": "Bash", "tool_input": {"command": "sed -i 's/a/b/' learning/validator.py"}}, tmp_path) == 2
    assert _guard({"tool_name": "Bash", "tool_input": {"command": "cat learning/validator.py"}}, tmp_path) == 0
    (tmp_path / ".harness_unlock").touch()
    assert _guard(edit, tmp_path) == 0
