import os
from typing import Literal

from langgraph.graph import StateGraph, END

from src.state import ABSAState
from src.agents.supervisor import supervisor
from src.agents.extractor import aspect_extractor
from src.agents.classifier import sentiment_classifier
from src.agents.critic import critic
from src.agents.synthesizer import insight_synthesizer


def _route_after_critic(state: ABSAState) -> Literal["revise", "pass"]:
    if state["verdict"] == "REVISE" and state["revisions"] < state["max_revisions"]:
        return "revise"
    return "pass"


def build_graph() -> StateGraph:
    graph = StateGraph(ABSAState)

    graph.add_node("supervisor", supervisor)
    graph.add_node("aspect_extractor", aspect_extractor)
    graph.add_node("sentiment_classifier", sentiment_classifier)
    graph.add_node("critic", critic)
    graph.add_node("insight_synthesizer", insight_synthesizer)

    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "aspect_extractor")
    graph.add_edge("aspect_extractor", "sentiment_classifier")
    graph.add_edge("sentiment_classifier", "critic")
    graph.add_conditional_edges(
        "critic",
        _route_after_critic,
        {
            "revise": "sentiment_classifier",
            "pass": "insight_synthesizer",
        },
    )
    graph.add_edge("insight_synthesizer", END)

    return graph.compile()


# 싱글턴 — main.py와 테스트에서 import해서 사용
app = build_graph()
