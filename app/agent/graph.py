from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    check_budget,
    fetch_ingredients,
    generate_plan,
    retrieve_context,
    save_plan,
    validate_nutrition,
)
from app.agent.state import AgentState

MAX_RETRIES = 3


def _should_regenerate(state: AgentState) -> str:
    if state["validation_errors"] and state["retry_count"] < MAX_RETRIES:
        return "generate_plan"
    return "check_budget"


def _after_generate(state: AgentState) -> str:
    if state.get("error"):
        return END
    return "validate_nutrition"


def build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("fetch_ingredients", fetch_ingredients)
    g.add_node("retrieve_context", retrieve_context)
    g.add_node("generate_plan", generate_plan)
    g.add_node("validate_nutrition", validate_nutrition)
    g.add_node("check_budget", check_budget)
    g.add_node("save_plan", save_plan)

    # fetch_ingredients와 retrieve_context 병렬 실행 후 generate_plan에서 합류
    g.add_edge(START, "fetch_ingredients")
    g.add_edge(START, "retrieve_context")
    g.add_edge("fetch_ingredients", "generate_plan")
    g.add_edge("retrieve_context", "generate_plan")
    g.add_conditional_edges(
        "generate_plan",
        _after_generate,
        {"validate_nutrition": "validate_nutrition", END: END},
    )
    g.add_conditional_edges(
        "validate_nutrition",
        _should_regenerate,
        {"generate_plan": "generate_plan", "check_budget": "check_budget"},
    )
    g.add_edge("check_budget", "save_plan")
    g.add_edge("save_plan", END)

    return g


meal_plan_graph = build_graph().compile()
