from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable

from src.state import ABSAState
from src.utils import llm_json as _llm, parse_json_response

_SYSTEM = """\
# Role
당신은 ASTE 결과의 품질을 검증하는 QA 전문가입니다.
추출된 결과의 정확성과 완결성을 검사하고 PASS 또는 REVISE를 판정합니다.

# Instructions
- 원본 리뷰와 ASTE 결과를 대조해 4가지 항목을 검사하세요
- 전체 신뢰도와 검사 결과를 종합해 최종 판정을 내리세요
- REVISE 판정 시 구체적인 오류 위치와 수정 방향을 feedback에 작성하세요

# Steps
1. Hallucination 검사: 각 결과의 opinion이 리뷰 원문에 실제로 존재하는지 확인합니다
2. Evidence 검사: evidence 필드가 리뷰 원문을 정확히 인용하는지 확인합니다
3. Sentiment 일관성: opinion의 의미와 sentiment 레이블이 일치하는지 확인합니다
4. Coverage 검사: 리뷰에 언급된 중요 aspect 중 누락된 것이 있는지 확인합니다
5. 신뢰도 >= 0.7 AND 1~4 모두 통과 → PASS, 하나라도 실패 → REVISE 판정합니다

# Expectations
출력 형식 (JSON):
{"verdict": "PASS|REVISE", "feedback": "REVISE 시 오류 번호와 수정 방향 명시. PASS 시 null"}

REVISE 예시:
{"verdict": "REVISE", "feedback": "1. '데이터 속도' opinion '빠르다'가 원문에 없음. 원문은 '느리다'이므로 NEG로 수정 필요.\n2. '고객 서비스' aspect 누락. '상담원이 불친절했다' 표현에서 추출 필요."}

# Narrowing
- aste_results 필드를 직접 수정하지 마세요 (판정만 수행)
- feedback에 "더 잘 해주세요" 수준의 막연한 지시 금지 — 오류 위치와 수정 방향 필수
- confidence 값을 변경하지 마세요
"""


def _format_aste_results(aste_results: list) -> str:
    lines = []
    for i, t in enumerate(aste_results, 1):
        lines.append(
            f"{i}. aspect={t['aspect']}, opinion={t['opinion']}, "
            f"sentiment={t['sentiment']}, confidence={t['confidence']:.2f}\n"
            f"   evidence: {t['evidence']}"
        )
    return "\n".join(lines)


@traceable(name="critic")
def critic(state: ABSAState) -> dict:
    reviews = state["reviews"]
    aste_results = state["aste_results"]
    confidence = state["confidence"]
    revisions = state.get("revisions", 0)

    reviews_str = "\n".join(f"- {r}" for r in reviews)
    human = f"""\
## 원본 리뷰
{reviews_str}

## 추출된 ASTE 결과
{_format_aste_results(aste_results)}

## 전체 신뢰도
{confidence:.2f}
"""

    response = _llm.invoke([SystemMessage(_SYSTEM), HumanMessage(human)])
    parsed = parse_json_response(response)

    return {
        "verdict": parsed.get("verdict", "REVISE"),
        "critic_feedback": parsed.get("feedback"),
        "revisions": revisions + 1,
    }
