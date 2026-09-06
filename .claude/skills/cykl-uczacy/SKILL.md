---
name: cykl-uczacy
description: Przeprowadzenie jednego cyklu uczącego agenta self-harness (weakness mining → propozycja → walidacja → rekomendacja dla człowieka) i diagnoza, gdy cykl nie daje kandydata. Używaj zawsze, gdy użytkownik chce uruchomić, sprawdzić lub debugować pętlę uczącą, cykl, daemon, weakness mining, kandydata harnessu albo walidację.
---
# Cykl uczący

## Przebieg
1. Upewnij się, że jest baseline: `python -m eval.run_regression --out data/baseline.json`. Bez porażek w logu mining nie ma na czym pracować, wtedy zaproponuj nowe, trudniejsze zadania do `eval/regression/proposed_tasks.jsonl`.
2. `python -m learning.daemon --once`. Przeczytaj JSON podsumowania: `clusters`, `memory_writes`, `candidates`, `validations`.
3. Jeśli jest kandydat: uruchom subagenta `walidator` na raporcie z `data/validations/`. Przekaż użytkownikowi rekomendację i dokładną komendę promocji:
   `touch data/approvals/<kandydat>.ok && python -m learning.promote harness/candidates/<kandydat>.yaml`
4. Jeśli poziom 1 (wpis do `memory/skills/`): sprawdź, czy skill jest konkretny i krótki, w razie potrzeby popraw treść (to nie jest plik chroniony).
5. Jeśli poziom 3: zapisz obserwację w podsumowaniu, to kandydat do M5 (fine-tuning), nie do zmiany promptu.

## Gdy cykl nic nie daje
- `clusters: 0` przy istniejących porażkach: krytyk nie zwrócił JSON. Sprawdź event `mining` z polem `error` i surową odpowiedź, popraw parsowanie w `learning/common.py` albo prompt w `weakness_mining.py`.
- kandydat odrzucony przez `only_editable_changed`: proposer zmienił chronione pole, popraw prompt w `proposer.py`.
- walidacja trwa zbyt długo: użyj `--ids` w `eval.run_regression`, żeby przetestować podzbiór, ale pełna walidacja przed promocją jest obowiązkowa.

## Zasady
- Jeden kandydat na cykl. Nie łącz kilku zmian w jednego kandydata.
- Każdy kandydat ma plik `.md` z dowodami (run_id). Bez dowodów nie ma propozycji.
- Nie edytujesz plików chronionych (lista w CLAUDE.md). Nie tworzysz plików zgody.
