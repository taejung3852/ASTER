import json
from collections import defaultdict

from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable

from src.state import ABSAState
from src.utils import llm_text as _llm

_SYSTEM = """\
# Role
당신은 고객 경험 전략 컨설턴트입니다.
감성 분석 집계 데이터를 바탕으로 운영팀이 즉시 실행 가능한 액션 권고문을 작성합니다.

# Instructions
- 집계 결과의 수치를 반드시 인용하세요
- 우선순위가 높은 이슈(NEG 비율 높은 순)부터 작성하세요
- 각 권고사항은 구체적인 실행 액션을 포함해야 합니다

# Steps
1. 상위 부정 이슈를 NEG 비율 기준으로 우선순위를 정합니다
2. 각 이슈에 대해 수치를 인용한 문제 정의를 작성합니다
3. 문제에 대응하는 구체적 운영 액션을 제안합니다
4. 최대 5개, 우선순위 순서로 정렬해 반환합니다

# Expectations
형식: "X 관련 부정 감성 Y% → [구체적 권고 액션]"

예시:
1. 요금 관련 부정 감성 75% → 가성비 요금제 신설 또는 기존 요금제 혜택 재설계 검토
2. 데이터 속도 불만 33% → 혼잡 지역 네트워크 증설 우선순위 지정

# Narrowing
- 수치 없는 권고 금지 (반드시 집계 결과 인용)
- "개선이 필요합니다" 수준의 막연한 문장 금지
- 최대 5개 초과 금지
"""


def _aggregate(aste_results: list) -> dict:
    stats = defaultdict(lambda: {"POS": 0, "NEG": 0, "NEU": 0, "total": 0})
    for t in aste_results:
        cat = t["aspect"]
        stats[cat][t["sentiment"]] += 1
        stats[cat]["total"] += 1
    result = {}
    for cat, s in stats.items():
        total = s["total"]
        result[cat] = {
            **s,
            "neg_ratio": round(s["NEG"] / total, 3) if total > 0 else 0.0,
        }
    return result


def _format_stats(stats: dict) -> str:
    lines = []
    for aspect, s in sorted(stats.items(), key=lambda x: -x[1]["neg_ratio"]):
        lines.append(
            f"- {aspect}: POS={s['POS']}, NEG={s['NEG']}, NEU={s['NEU']} "
            f"(NEG 비율 {s['neg_ratio']*100:.1f}%)"
        )
    return "\n".join(lines)


@traceable(name="insight_synthesizer")
def insight_synthesizer(state: ABSAState) -> dict:
    aste_results = state["aste_results"]
    domain = state["domain"]
    revisions_used = state.get("revisions", 0)

    aggregated_stats = _aggregate(aste_results)

    top_negatives = sorted(
        aggregated_stats.items(), key=lambda x: -x[1]["neg_ratio"]
    )[:3]
    top_neg_str = "\n".join(
        f"- {k}: NEG 비율 {v['neg_ratio']*100:.1f}%" for k, v in top_negatives
    )

    human = f"""\
## 분석 도메인
{domain}

## 감성 분석 집계 결과
{_format_stats(aggregated_stats)}

## 상위 부정 이슈 (NEG 비율 상위 3개)
{top_neg_str or "없음"}
"""

    response = _llm.invoke([SystemMessage(_SYSTEM), HumanMessage(human)])
    action_recommendations = response.content.strip()

    final_report = json.dumps(
        {
            "domain": domain,
            "review_count": len(state["reviews"]),
            "aste_results": aste_results,
            "aggregated_stats": aggregated_stats,
            "action_recommendations": action_recommendations,
            "revisions_used": revisions_used,
        },
        ensure_ascii=False,
        indent=2,
    )

    return {
        "aggregated_stats": aggregated_stats,
        "action_recommendations": action_recommendations,
        "final_report": final_report,
    }
