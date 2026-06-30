from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    check_budget,
    check_single_budget,
    compute_metrics,
    fetch_ingredients,
    generate_plan,
    generate_qa,
    generate_single_meal,
    resolve_excluded_names,
    retrieve_context,
    retrieve_single_context,
    save_plan,
    save_single_plan,
    score_ingredients,
    score_ingredients_single,
    validate_nutrition,
    validate_single_nutrition,
)
from app.agent.state import AgentState, SingleMealState

MAX_RETRIES = 2


def _should_regenerate(state: AgentState) -> str:
    errors = state["validation_errors"]
    if errors and state["retry_count"] < MAX_RETRIES:
        return "generate_plan"
    if errors:  # 재시도 소진, 오류 잔존 → 저장 생략
        return END
    return "check_budget"


def _after_generate(state: AgentState) -> str:
    if state.get("error"):
        return END
    return "validate_nutrition"


def build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("fetch_ingredients", fetch_ingredients)
    g.add_node("score_ingredients", score_ingredients)
    g.add_node("retrieve_context", retrieve_context)
    g.add_node("generate_plan", generate_plan)
    g.add_node("validate_nutrition", validate_nutrition)
    g.add_node("check_budget", check_budget)
    g.add_node("compute_metrics", compute_metrics)
    g.add_node("save_plan", save_plan)

    # fetch_ingredients → score_ingredients → generate_plan (병렬: retrieve_context → generate_plan)
    g.add_edge(START, "fetch_ingredients")
    g.add_edge(START, "retrieve_context")
    g.add_edge("fetch_ingredients", "score_ingredients")
    g.add_edge("score_ingredients", "generate_plan")
    g.add_edge("retrieve_context", "generate_plan")
    g.add_conditional_edges(
        "generate_plan",
        _after_generate,
        {"validate_nutrition": "validate_nutrition", END: END},
    )
    g.add_conditional_edges(
        "validate_nutrition",
        _should_regenerate,
        {"generate_plan": "generate_plan", "check_budget": "check_budget", END: END},
    )
    g.add_edge("check_budget", "compute_metrics")
    g.add_edge("compute_metrics", "save_plan")
    g.add_edge("save_plan", END)

    return g


meal_plan_graph = build_graph().compile()


def _after_single_generate(state: SingleMealState) -> str:
    if state.get("error"):
        return END
    return "validate_single_nutrition"


def _should_single_regenerate(state: SingleMealState) -> str:
    errors = state.get("validation_errors", [])
    if errors and state.get("retry_count", 0) < MAX_RETRIES:
        return "generate_single_meal"
    if errors:
        return END    # 재시도 소진 → 저장 생략
    return "generate_qa"


def build_single_meal_graph() -> StateGraph:
    g = StateGraph(SingleMealState)

    g.add_node("resolve_excluded", resolve_excluded_names)
    g.add_node("retrieve_context", retrieve_single_context)
    g.add_node("score_ingredients_single", score_ingredients_single)
    g.add_node("generate_single_meal", generate_single_meal)
    g.add_node("validate_single_nutrition", validate_single_nutrition)
    g.add_node("generate_qa", generate_qa)
    g.add_node("check_single_budget", check_single_budget)
    g.add_node("save_single_plan", save_single_plan)

    # resolve_excluded와 retrieve_context 병렬 후 score_ingredients_single에서 합류
    g.add_edge(START, "resolve_excluded")
    g.add_edge(START, "retrieve_context")
    g.add_edge("resolve_excluded", "score_ingredients_single")
    g.add_edge("retrieve_context", "score_ingredients_single")
    g.add_edge("score_ingredients_single", "generate_single_meal")
    g.add_conditional_edges(
        "generate_single_meal",
        _after_single_generate,
        {"validate_single_nutrition": "validate_single_nutrition", END: END},
    )
    g.add_conditional_edges(
        "validate_single_nutrition",
        _should_single_regenerate,
        {"generate_single_meal": "generate_single_meal",
         "generate_qa": "generate_qa",
         END: END},
    )
    g.add_edge("generate_qa", "check_single_budget")
    g.add_edge("check_single_budget", "save_single_plan")
    g.add_edge("save_single_plan", END)

    return g


single_meal_graph = build_single_meal_graph().compile()
