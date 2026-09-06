# self-harness-agent

Agent LLM działający long-running, który uczy się na trzech poziomach:
1. kontekst/pamięć (fakty, skille proceduralne w `memory/`),
2. harness (`harness/harness.yaml`: prompt systemowy, narzędzia, polityki), modyfikowany pętlą Self-Harness: weakness mining → propozycja → walidacja regresyjna → promocja,
3. wagi (opcjonalnie, później: LoRA na zweryfikowanych trajektoriach).

Język komunikacji: polski. Kod: Python 3.11+, proste skrypty, bez frameworków UI. Komentarze krótkie.

## Architektura (nie zmieniać bez uzgodnienia)

- `agent/` pętla wykonawcza (LangGraph). Harness jest DANYMI wczytywanymi ze `harness/harness.yaml`, nie kodem.
- `agent/event_log.py` append-only log epizodów (SQLite w `data/events.sqlite`). Jedyne źródło prawdy. Nigdy UPDATE/DELETE.
- `learning/` pętla ucząca: `weakness_mining.py` → `proposer.py` → `validator.py` → `promote.py`, sterowana przez `daemon.py`.
- `eval/regression/tasks.jsonl` zamrożony zestaw regresyjny z weryfikatorami (`eval/verifiers.py`).
- `harness/candidates/` kandydaci na nowy harness, każdy z plikiem `.md` z uzasadnieniem.
- `data/validations/` raporty walidacji, `data/approvals/` zgody człowieka na promocję.

## Niezmienniki (egzekwowane hookiem `.claude/hooks/guard_harness.py`)

Bez pliku `.harness_unlock` w katalogu projektu NIE edytujesz:
- `harness/harness.yaml` (zmiany tylko przez `learning/promote.py`),
- `eval/regression/`, `eval/verifiers.py`, `eval/run_regression.py`,
- `learning/validator.py`, `learning/promote.py`,
- `.claude/hooks/`, `.claude/settings.json`.

Powód: agent nie może modyfikować własnego walidatora ani zestawu regresyjnego. Jeśli uważasz, że któryś z tych plików wymaga zmiany, opisz co i dlaczego, człowiek utworzy `.harness_unlock`.

Kandydat na harness może zmieniać tylko pola z `EDITABLE_FIELDS` w `harness/schema.py`. Promocja wymaga zaakceptowanego raportu walidacji i pliku zgody w `data/approvals/`.

## Komendy

```
pip install -e ".[dev]"
LLM_PROVIDER=fake python -m eval.run_regression          # smoke test bez modelu
python -m eval.run_regression                            # z Ollamą
python -m scripts.run_task "treść zadania"               # pojedyncze zadanie
python -m learning.daemon --once                         # jeden cykl uczący
python -m learning.daemon                                # tryb long-running (STOP: touch data/STOP)
pytest -q
```

Modele: Ollama lokalnie (`OLLAMA_BASE_URL` w `.env`). `LLM_PROVIDER=fake` nadpisuje providera na potrzeby testów.

## Zasady pracy

- Zanim coś zaimplementujesz, sprawdź `ROADMAP.md` i pracuj nad bieżącym kamieniem milowym.
- Każda zmiana kodu: `pytest -q` przechodzi, `LLM_PROVIDER=fake python -m eval.run_regression` przechodzi.
- Nowe zadania regresyjne proponuj w `eval/regression/proposed_tasks.jsonl` (dozwolone), człowiek przenosi je do `tasks.jsonl`.
- Nie dodawaj zależności bez potrzeby. Nie używaj płatnych API bez wyraźnej zgody.
- Eksperymenty badawcze (porównania wariantów, ablacje) prowadź zgodnie ze skillem `protokol-badawczy`, jeśli jest zainstalowany.
- Subagenci: `krytyk` do weakness mining i diagnozy poziomu, `walidator` do interpretacji raportów walidacji. Skill `cykl-uczacy` opisuje pełny przebieg cyklu.

## Kontrakty danych

Event log, kolumny: `id, ts, run_id, harness_version, kind, payload(JSON)`.
Rodzaje `kind`: `task_start, llm_call, tool_call, tool_result, task_end, mining, proposal, validation, promotion`.
`task_end.payload` zawiera: `ok, answer, steps, verifier_reason, task_id`.

Zadanie regresyjne (JSONL): `{"id", "prompt", "verifier": {"type", ...}, "protected": bool}`.
Typy weryfikatorów: `answer_contains, answer_regex, file_exists, file_contains`.
