from __future__ import annotations

import argparse
from typing import TypedDict

from langgraph.graph import END, StateGraph

from .llm import complete
from .parser import ModelDecision, parse_decision
from .prompts import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from .tools import run_kali_command
from .skills import get_relevant_skills


class AgentState(TypedDict):
    objective: str
    history: list[str]
    decision: ModelDecision | None
    final: str | None
    iterations: int
    max_iterations: int
    prompt_tokens: int
    completion_tokens: int


def call_model(state: AgentState) -> AgentState:
    history = "\n\n".join(state["history"]) or "<none>"
    
    # Retrieve relevant skills based on objective and history
    skills_context = get_relevant_skills(state["objective"], state["history"])
    system_content = f"{SYSTEM_PROMPT}\n\n{skills_context}"
    
    content, prompt_tokens, completion_tokens = complete(
        [
            {"role": "system", "content": system_content},
            {
                "role": "user",
                "content": NEXT_STEP_PROMPT.format(
                    objective=state["objective"],
                    history=history,
                ),
            },
        ]
    )
    decision = parse_decision(content)
    
    import shutil
    terminal_width = shutil.get_terminal_size().columns
    token_msg = f"[Tokens | In: {prompt_tokens} Out: {completion_tokens}]"
    print(f"{token_msg:>{terminal_width}}")
    
    return {
        **state, 
        "decision": decision, 
        "prompt_tokens": state.get("prompt_tokens", 0) + prompt_tokens,
        "completion_tokens": state.get("completion_tokens", 0) + completion_tokens
    }


def execute_command(state: AgentState) -> AgentState:
    decision = state["decision"]
    if decision is None or decision.kind != "action" or not decision.command:
        return state

    try:
        result = run_kali_command(decision.command)
        entry = result.format_for_model()
    except Exception as exc:
        entry = f"$ {decision.command}\nerror: {exc}"

    return {
        **state,
        "history": [*state["history"], entry],
        "iterations": state["iterations"] + 1,
    }


def route_after_model(state: AgentState) -> str:
    decision = state["decision"]
    if decision is None:
        return "finish"
    if decision.kind == "final":
        return "finish"
    if state["iterations"] >= state["max_iterations"]:
        return "finish"
    return "execute"


def finish(state: AgentState) -> AgentState:
    decision = state["decision"]
    if decision and decision.kind == "final":
        final = decision.final
    else:
        final = "Stopped before completion because the iteration limit was reached."
    return {**state, "final": final}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("model", call_model)
    graph.add_node("execute", execute_command)
    graph.add_node("finish", finish)

    graph.set_entry_point("model")
    graph.add_conditional_edges(
        "model",
        route_after_model,
        {"execute": "execute", "finish": "finish"},
    )
    graph.add_edge("execute", "model")
    graph.add_edge("finish", END)
    return graph.compile()


def run(objective: str, max_iterations: int = 6) -> str:
    app = build_graph()
    result = app.invoke(
        {
            "objective": objective,
            "history": [],
            "decision": None,
            "final": None,
            "iterations": 0,
            "max_iterations": max_iterations,
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }
    )
    return result["final"] or ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LangGraph Kali agent.")
    parser.add_argument("objective", nargs="?", help="Authorized security testing objective.")
    parser.add_argument("--max-iterations", type=int, default=6)
    args = parser.parse_args()
    
    if args.objective:
        print(run(args.objective, max_iterations=args.max_iterations))
    else:
        print("LangGraph Kali Agent Interactive Mode")
        while True:
            try:
                objective = input("\nEnter objective (or 'exit' to quit): ")
                if objective.strip().lower() in ['exit', 'quit']:
                    break
                if not objective.strip():
                    continue
                print(run(objective, max_iterations=args.max_iterations))
            except (KeyboardInterrupt, EOFError):
                print("\nExiting...")
                break


if __name__ == "__main__":
    main()
