# self-harness-agent

Szkielet agenta LLM long-running z samodoskonaleniem (pamięć → harness → wagi). Szczegóły w `CLAUDE.md` i `ROADMAP.md`.

## Start

```
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
LLM_PROVIDER=fake python -m eval.run_regression   # smoke test bez modelu
python -m eval.run_regression                     # wymaga działającej Ollamy i modelu z harness.yaml
```

## Praca z Claude Code

Otwórz katalog w Claude Code. Hooki z `.claude/settings.json` ładują się automatycznie: przy starcie sesji dostajesz stan projektu, a edycja chronionych plików jest blokowana do czasu utworzenia `.harness_unlock`.

Pierwsze polecenie dla Claude Code: "Zrealizuj M0 z ROADMAP.md".
