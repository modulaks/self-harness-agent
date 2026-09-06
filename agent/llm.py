"""Fabryka modeli. LLM_PROVIDER=fake nadpisuje providera (smoke testy bez Ollamy)."""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from agent.config import LLM_PROVIDER_OVERRIDE, OLLAMA_BASE_URL
from harness.schema import ModelSpec


class FakeLLM:
    """Odbija ostatnią wiadomość użytkownika. Nie woła narzędzi."""

    def bind_tools(self, tools):
        return self

    def invoke(self, messages, **kwargs):
        last = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        text = last.content if last else ""
        return AIMessage(content=f"FAKE: {text}")


def make_llm(spec: ModelSpec):
    provider = LLM_PROVIDER_OVERRIDE or spec.provider
    if provider == "fake":
        return FakeLLM()
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=spec.name, temperature=spec.temperature, base_url=OLLAMA_BASE_URL)
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=spec.name, temperature=spec.temperature)
    raise ValueError(f"nieznany provider: {provider}")
