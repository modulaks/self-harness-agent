"""Narzędzia agenta. Wszystkie operacje plikowe ograniczone do SANDBOX_DIR."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from langchain_core.tools import tool

from agent.config import SANDBOX_DIR

MAX_OUT = 6000
TIMEOUT_S = 60


def _safe(rel: str) -> Path:
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    p = (SANDBOX_DIR / rel).resolve()
    if SANDBOX_DIR.resolve() not in p.parents and p != SANDBOX_DIR.resolve():
        raise ValueError(f"ścieżka poza sandboksem: {rel}")
    return p


def _clip(s: str) -> str:
    return s if len(s) <= MAX_OUT else s[:MAX_OUT] + f"\n...[obcięto, {len(s)} znaków]"


@tool
def list_dir(path: str = ".") -> str:
    """Listuje pliki i katalogi w sandboksie (ścieżka względna)."""
    p = _safe(path)
    if not p.exists():
        return f"brak: {path}"
    return "\n".join(sorted(f"{'d ' if c.is_dir() else 'f '}{c.name}" for c in p.iterdir())) or "(pusto)"


@tool
def read_file(path: str) -> str:
    """Czyta plik tekstowy z sandboksu."""
    p = _safe(path)
    if not p.is_file():
        return f"brak pliku: {path}"
    return _clip(p.read_text(encoding="utf-8", errors="replace"))


@tool
def write_file(path: str, content: str) -> str:
    """Zapisuje plik tekstowy w sandboksie (nadpisuje)."""
    p = _safe(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"zapisano {path} ({len(content)} znaków)"


@tool
def run_python(code: str) -> str:
    """Uruchamia kod Pythona w sandboksie (cwd = sandbox), zwraca stdout+stderr."""
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run(
            [sys.executable, "-c", code], cwd=SANDBOX_DIR, capture_output=True, text=True, timeout=TIMEOUT_S
        )
    except subprocess.TimeoutExpired:
        return f"timeout po {TIMEOUT_S}s"
    out = r.stdout + (("\n[stderr]\n" + r.stderr) if r.stderr else "")
    return _clip(out or f"(brak wyjścia, kod {r.returncode})")


TOOL_REGISTRY = {t.name: t for t in (list_dir, read_file, write_file, run_python)}


def get_tools(names: list[str]):
    unknown = [n for n in names if n not in TOOL_REGISTRY]
    if unknown:
        raise ValueError(f"nieznane narzędzia w harnessie: {unknown}")
    return [TOOL_REGISTRY[n] for n in names]


def reset_sandbox() -> None:
    if SANDBOX_DIR.exists():
        for c in SANDBOX_DIR.iterdir():
            if c.name == ".gitkeep":
                continue
            shutil.rmtree(c) if c.is_dir() else c.unlink()
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
