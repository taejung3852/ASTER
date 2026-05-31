from src.state import ABSAState, DOMAIN_TAXONOMY


def supervisor(state: ABSAState) -> ABSAState:
    if not state.get("reviews"):
        raise ValueError("reviews는 비어있을 수 없습니다")
    if state.get("domain") not in DOMAIN_TAXONOMY:
        raise ValueError(f"domain은 {list(DOMAIN_TAXONOMY.keys())} 중 하나여야 합니다")

    return {
        **state,
        "aspects": [],
        "aste_results": [],
        "revisions": 0,
        "max_revisions": state.get("max_revisions", 3),
        "confidence": 0.0,
        "verdict": "REVISE",
        "critic_feedback": None,
        "graph_context": None,
        "vector_context": None,
        "low_confidence_items": [],
        "aggregated_stats": {},
        "action_recommendations": "",
        "final_report": "",
    }
