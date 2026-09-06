# ROADMAP

Kamienie milowe realizowane po kolei. Każdy ma definicję ukończenia (DoD). Bieżący: M0.

## M0 Środowisko i smoke test
- `pip install -e ".[dev]"` działa, `pytest -q` zielony.
- `LLM_PROVIDER=fake python -m eval.run_regression` przechodzi zadanie `smoke-echo`.
- Hook `guard_harness.py` blokuje edycję `harness/harness.yaml` (sprawdź ręcznie: poproś Claude Code o edycję, ma odmówić).
DoD: powyższe trzy punkty.

## M1 Pętla wykonawcza na Ollamie
- `agent/graph.py` działa z modelem z `harness.yaml` (executor), narzędzia `read_file, write_file, list_dir, run_python` w sandboksie.
- Każdy krok zapisany w event logu (`llm_call`, `tool_call`, `tool_result`).
- Zestaw regresyjny rozszerzony do ok. 10 zadań (propozycje w `eval/regression/proposed_tasks.jsonl`), w tym 3 oznaczone `protected: true`.
- Baseline: `python -m eval.run_regression --out data/baseline.json`.
DoD: pass rate baseline zapisany, log zawiera pełne trajektorie.

## M2 Weakness mining i proposer
- `learning/weakness_mining.py` zwraca klastry porażek z mechanizmem przyczynowym i poziomem (1/2/3), model krytyk z `harness.yaml`.
- `learning/proposer.py` generuje kandydata w `harness/candidates/` zmieniającego tylko `EDITABLE_FIELDS`, z plikiem `.md` z uzasadnieniem i listą `run_id` dowodowych (proweniencja).
- Poziom 1 (luka wiedzy) trafia do `memory/skills/*.md` lub `memory/facts.jsonl`, nie do harnessu.
DoD: jeden cykl `python -m learning.daemon --once` kończy się kandydatem albo wpisem do pamięci.

## M3 Walidacja i promocja
- `learning/validator.py` porównuje harness bieżący vs kandydat na tym samym zestawie, reguła akceptacji: pass rate ≥ bieżący + `min_delta`, zero regresji na zadaniach `protected`.
- `learning/promote.py` promuje tylko z raportem `accepted: true` i plikiem zgody `data/approvals/<candidate>.ok`; bumpuje wersję, commit + tag w git, event `promotion`.
- Rollback: `git checkout <tag> -- harness/harness.yaml`.
DoD: pierwsza promocja przeszła przez pełną ścieżkę z udziałem człowieka.

## M4 Long-running
- `learning/daemon.py` jako proces: wyzwalacz co N nowych epizodów lub co T minut, budżet tokenów/kosztu na cykl, kill switch `data/STOP`.
- Event log na Postgresie (`docker-compose.yml`), pgvector do retrievalu epizodów, Langfuse self-hosted do tracingu.
- Metryki cyklu: liczba kandydatów, odsetek zaakceptowanych, trend pass rate w czasie.
DoD: daemon przepracował 24h bez interwencji, raport trendu.

## M5 (opcjonalnie) Poziom 3, wagi
- Eksport zweryfikowanych trajektorii (`task_end.ok == true`) do formatu SFT/DPO.
- TRL + Unsloth LoRA, konwersja GGUF, redeploy do Ollamy jako nowa wersja executora.
- Nowy model przechodzi tę samą walidację co kandydat harnessu.
DoD: porównanie executor v0 vs v1 na zestawie regresyjnym, zgodnie z protokołem badawczym.

## Poza zakresem na teraz
- UI, dashboardy.
- Płatne API jako executor.
- Modyfikacja walidatora przez agenta (nigdy).
