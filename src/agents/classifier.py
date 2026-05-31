import json
from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable

from src.state import ABSAState, ASTEResult
from src.utils import llm_json as _llm

_SYSTEM = """\
# Role
당신은 ASTE(Aspect-Sentiment Triple Extraction) 전문가입니다.
주어진 리뷰에서 aspect별 opinion과 sentiment를 추출하고, 판단 근거를 명시합니다.

# Instructions
- 추출된 Aspect 목록의 각 항목에 대해 ASTE 삼중을 추출하세요
- GraphRAG 컨텍스트를 참고해 감성 판단의 정확도를 높이세요
- 모든 판단에 리뷰 원문을 직접 인용한 evidence를 작성하세요

# Steps
1. 각 aspect에 대해 리뷰에서 해당 표현을 찾습니다
2. opinion: aspect에 대한 평가 표현을 원문에서 추출합니다
3. sentiment: opinion의 감성을 POS / NEG / NEU 중 하나로 판정합니다
4. confidence: 이 판정의 확신도를 0.0~1.0으로 산정합니다
5. evidence: 판단 근거가 된 리뷰 원문 구절을 직접 인용합니다
6. aspect가 리뷰에 언급되지 않았으면 결과에서 제외합니다

# Expectations
출력 형식 (JSON):
{"aste_results": [{"aspect": "str", "opinion": "str", "sentiment": "POS|NEG|NEU", "confidence": 0.0, "evidence": "원문 인용"}]}

예시:
{"aste_results": [{"aspect": "요금", "opinion": "너무 비싸", "sentiment": "NEG", "confidence": 0.87, "evidence": "원문: '요금이 너무 비싸서 해지를 고려하고 있어요'"}]}

# Narrowing
- 리뷰에 없는 내용을 opinion으로 생성하지 마세요 (hallucination 금지)
- evidence는 반드시 리뷰 원문을 직접 인용해야 합니다 (빈 문자열 절대 금지)
- aspect가 리뷰에 없으면 해당 항목을 결과에서 제외하세요
"""


@traceable(name="sentiment_classifier")
def sentiment_classifier(state: ABSAState) -> dict:
    reviews = state["reviews"]
    aspects = state["aspects"]
    graph_context = state.get("graph_context")
    critic_feedback: Optional[str] = state.get("critic_feedback")

    reviews_str = "\n".join(f"- {r}" for r in reviews)
    aspects_str = "\n".join(f"- {a['text']} ({a['category']})" for a in aspects)
    feedback_section = (
        f"## Critic 피드백 (반드시 반영)\n{critic_feedback}\n\n위 피드백의 오류를 수정하여 다시 추출하세요.\n\n"
        if critic_feedback
        else ""
    )

    human = f"""\
{feedback_section}## 분석할 리뷰
{reviews_str}

## 추출된 Aspect 목록
{aspects_str}

## GraphRAG 컨텍스트
{graph_context or "없음"}
"""

    response = _llm.invoke([SystemMessage(_SYSTEM), HumanMessage(human)])
    parsed = json.loads(response.content)
    aste_results: list[ASTEResult] = parsed.get("aste_results", [])

    for t in aste_results:
        if not t.get("evidence"):
            raise ValueError(f"evidence 필드가 비어있습니다: {t}")

    confidence = (
        sum(t["confidence"] for t in aste_results) / len(aste_results)
        if aste_results
        else 0.0
    )

    return {"aste_results": aste_results, "confidence": confidence}
