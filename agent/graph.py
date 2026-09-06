"""Pętla wykonawcza: LangGraph, dwa węzły (agent, tools). Każdy krok trafia do event logu."""
from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from agent.event_log import EventLog, new_run_id
from agent.llm import make_llm
from agent.memory import load_skills_text
from agent.tools import get_tools
from harness.schema import Harness


class State(TypedDict):
    messages: Annotated[list, add_messages]
    steps: int


def _msg_dump(m) -> dict:
    d = {"type": m.__class__.__name__, "content": m.content if isinstance(m.content, str) else str(m.content)}
    if getattr(m, "tool_calls", None):
        d["tool_calls"] = m.tool_calls
    return d


def build_graph(harness: Harness, log: EventLog, run_id: str):
    tools = get_tools(harness.tools)
    llm = make_llm(harness.executor)
    if tools:
        llm = llm.bind_tools(tools)
    skills = load_skills_text(harness.memory)
    system = harness.system_prompt + (f"\n\n# Skille\n{skills}" if skills else "")

    def agent_node(state: State):
        resp = llm.invoke([SystemMessage(content=system)] + state["messages"])
        log.append(run_id, harness.version, "llm_call", {"step": state["steps"], "response": _msg_dump(resp)})
        for tc in getattr(resp, "tool_calls", None) or []:
            log.append(run_id, harness.version, "tool_call", {"step": state["steps"], "name": tc["name"], "args": tc["args"]})
        return {"messages": [resp], "steps": state["steps"] + 1}

    tool_node = ToolNode(tools) if tools else None

    def tools_node(state: State):
        out = tool_node.invoke(state)
        for m in out["messages"]:
            log.append(run_id, harness.version, "tool_result", {"step": state["steps"], "name": getattr(m, "name", None), "content": str(m.content)[:harness.policies.max_output_chars]})
        return out

    def route(state: State):
        last = state["messages"][-1]
        if state["steps"] >= harness.policies.max_steps:
            return END
        if tools and getattr(last, "tool_calls", None):
            return "tools"
        return END

    g = StateGraph(State)
    g.add_node("agent", agent_node)
    if tools:
        g.add_node("tools", tools_node)
        g.add_edge("tools", "agent")
    g.set_entry_point("agent")
    g.add_conditional_edges("agent", route)
    return g.compile()


def run_task(harness: Harness, log: EventLog, prompt: str, task_id: str | None = None, run_id: str | None = None) -> dict:
    run_id = run_id or new_run_id()
    log.append(run_id, harness.version, "task_start", {"task_id": task_id, "prompt": prompt})
    graph = build_graph(harness, log, run_id)
    final = graph.invoke({"messages": [HumanMessage(content=prompt)], "steps": 0},
                         config={"recursion_limit": harness.policies.max_steps * 2 + 10})
    last = next((m for m in reversed(final["messages"]) if isinstance(m, AIMessage)), None)
    answer = (last.content if last else "") if isinstance(getattr(last, "content", ""), str) else str(last.content)
    return {"run_id": run_id, "answer": answer, "steps": final["steps"],
            "hit_max_steps": final["steps"] >= harness.policies.max_steps}


def finish_task(log: EventLog, harness: Harness, result: dict, ok: bool, reason: str, task_id: str | None) -> None:
    log.append(result["run_id"], harness.version, "task_end",
               {"task_id": task_id, "ok": ok, "verifier_reason": reason, "answer": result["answer"][:4000],
                "steps": result["steps"], "hit_max_steps": result["hit_max_steps"]})
