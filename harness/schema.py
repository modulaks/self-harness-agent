"""Model danych harnessu. Harness jest artefaktem wersjonowanym, nie kodem."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

# Pola, które proposer może zmieniać. Wszystko inne jest chronione.
EDITABLE_FIELDS = ("system_prompt", "tools", "policies", "memory")


class ModelSpec(BaseModel):
    provider: Literal["ollama", "anthropic", "fake"] = "ollama"
    name: str = "qwen3:8b"
    temperature: float = 0.2


class Policies(BaseModel):
    max_steps: int = 20
    tool_timeout_s: int = 60
    max_output_chars: int = 6000


class MemoryCfg(BaseModel):
    skills_dir: str = "memory/skills"
    facts_file: str = "memory/facts.jsonl"
    inject_skills: bool = True


class Harness(BaseModel):
    version: str
    executor: ModelSpec = Field(default_factory=ModelSpec)
    critic: ModelSpec = Field(default_factory=ModelSpec)
    system_prompt: str
    tools: list[str] = Field(default_factory=list)
    policies: Policies = Field(default_factory=Policies)
    memory: MemoryCfg = Field(default_factory=MemoryCfg)


def load_harness(path: str | Path) -> Harness:
    with open(path, encoding="utf-8") as f:
        return Harness.model_validate(yaml.safe_load(f))


def save_harness(h: Harness, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(h.model_dump(), f, allow_unicode=True, sort_keys=False)


def diff_fields(a: Harness, b: Harness) -> list[str]:
    """Nazwy pól najwyższego poziomu, które różnią się między a i b."""
    da, db = a.model_dump(), b.model_dump()
    return [k for k in da if da[k] != db.get(k)]


def only_editable_changed(current: Harness, candidate: Harness) -> tuple[bool, list[str]]:
    changed = diff_fields(current, candidate)
    illegal = [k for k in changed if k not in EDITABLE_FIELDS and k != "version"]
    return (not illegal, illegal)


def bump_patch(version: str) -> str:
    base = version.split("-")[0]
    major, minor, patch = (int(x) for x in base.split("."))
    return f"{major}.{minor}.{patch + 1}"
