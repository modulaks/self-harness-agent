"""Wspólne: wywołanie krytyka i parsowanie JSON z odpowiedzi."""
from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from agent.llm import make_llm
from harness.schema import Harness


def ask_critic(harness: Harness, system: str, user: str):
    llm = make_llm(harness.critic)
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return resp.content if isinstance(resp.content, str) else str(resp.content)


def parse_json(text: str):
    """Wyciąga pierwszy obiekt/listę JSON, toleruje płoty ```json."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)  # modele z reasoning
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
    if start < 0:
        return None
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        for end in range(len(text), start, -1):
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                continue
    return None
