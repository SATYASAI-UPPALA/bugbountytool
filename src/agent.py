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
    
    if decision.kind == "action":
        if decision.reason:
            print(f"\n[Agent Reasoning]: {decision.reason}")
    elif decision.kind == "final":
        if decision.final:
            print(f"\n[Agent Final]: {decision.final}")
    
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
        print(f"\n[Executing Tool]: {decision.command}")
        result = run_kali_command(decision.command)
        entry = result.format_for_model()
        print(f"[Tool Output]:\n{entry}")
    except Exception as exc:
        entry = f"$ {decision.command}\nerror: {exc}"
        print(f"[Tool Error]:\n{exc}")

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


def run(objective: str, max_iterations: int = 6, history: list[str] = None) -> tuple[str, list[str], int, int]:
    if history is None:
        history = []
    
    app = build_graph()
    result = app.invoke(
        {
            "objective": objective,
            "history": history,
            "decision": None,
            "final": None,
            "iterations": 0,
            "max_iterations": max_iterations,
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }
    )
    return result["final"] or "", result["history"], result.get("prompt_tokens", 0), result.get("completion_tokens", 0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LangGraph Kali agent.")
    parser.add_argument("objective", nargs="?", help="Authorized security testing objective.")
    parser.add_argument("--max-iterations", type=int, default=6)
    args = parser.parse_args()
    
    if args.objective:
        final_msg, _, _, _ = run(args.objective, max_iterations=args.max_iterations)
        print(final_msg)
    else:
        print("LangGraph Kali Agent Interactive Mode")
        print("Commands: 'update' to git pull, 'clear' to clear history, 'history' to view history, 'exit' to quit.")
        
        from .config import settings
        import shutil
        
        session_history = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        
        while True:
            try:
                terminal_width = shutil.get_terminal_size().columns
                stats_str = f"[Model: {settings.model} | Total Tokens - In: {total_prompt_tokens} Out: {total_completion_tokens}]"
                print(f"\n{stats_str:>{terminal_width}}")
                
                print("Enter objective or command:")
                cmd = input("> ").strip()
                cmd_lower = cmd.lower()
                
                if not cmd:
                    continue
                elif cmd_lower in ['exit', 'quit']:
                    break
                elif cmd_lower == 'update':
                    print("[System]: Updating tool via git pull...")
                    import subprocess
                    subprocess.run(["git", "pull"])
                    continue
                elif cmd_lower == 'clear':
                    session_history = []
                    print("[System]: Conversation history cleared.")
                    continue
                elif cmd_lower == 'history':
                    print("[System]: Current Conversation History:")
                    if not session_history:
                        print("  (empty)")
                    for idx, entry in enumerate(session_history):
                        print(f"[{idx}] {entry}")
                    continue
                
                final_msg, session_history, p_tokens, c_tokens = run(cmd, max_iterations=args.max_iterations, history=session_history)
                total_prompt_tokens += p_tokens
                total_completion_tokens += c_tokens
                print(final_msg)
            except (KeyboardInterrupt, EOFError):
                print("\nExiting...")
                break

if __name__ == "__main__":
    main()
