from typing import TypedDict, Literal, List, Optional

DOMAIN_TAXONOMY = {
    "telecom": [
        "요금", "데이터_속도", "통화_품질", "고객_서비스",
        "단말기", "부가서비스", "멤버십", "로밍", "인터넷", "개통_해지"
    ],
    "ecommerce": [
        "배송", "품질", "가격", "고객_서비스", "포장",
        "환불_교환", "상품_설명", "결제", "앱_UI", "브랜드"
    ],
}


class Aspect(TypedDict):
    text: str
    category: str


class ASTEResult(TypedDict):
    review_index: int
    aspect: str
    opinion: str
    sentiment: Literal["POS", "NEG", "NEU"]
    confidence: float
    evidence: str


class ABSAState(TypedDict):
    # 입력
    reviews: List[str]
    domain: Literal["telecom", "ecommerce"]

    # Extractor 출력
    aspects: List[Aspect]
    graph_context: Optional[str]
    vector_context: Optional[str]

    # Classifier 출력
    aste_results: List[ASTEResult]
    confidence: float

    # Critic 판정
    verdict: Literal["PASS", "REVISE"]
    revisions: int
    max_revisions: int
    critic_feedback: Optional[str]

    # HITL 대기열
    low_confidence_items: List[ASTEResult]

    # Synthesizer 출력
    aggregated_stats: dict
    action_recommendations: str
    final_report: str
