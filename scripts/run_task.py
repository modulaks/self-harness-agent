"""python -m scripts.run_task "treść zadania" """
import sys

from agent.config import EVENT_LOG_PATH, HARNESS_PATH
from agent.event_log import EventLog
from agent.graph import finish_task, run_task
from harness.schema import load_harness

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or "Powtórz dokładnie: PING"
    h = load_harness(HARNESS_PATH)
    log = EventLog(EVENT_LOG_PATH)
    r = run_task(h, log, prompt)
    finish_task(log, h, r, ok=True, reason="manual", task_id=None)
    print(f"[{r['run_id']}] kroki={r['steps']}\n{r['answer']}")
