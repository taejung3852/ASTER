# Agent Spec: Insight Synthesizer

## 도구 & LLM 설정
- **LLM:** `gemini-3.1-flash-lite` (via `langchain-google-genai`)
- **Temperature:** 0.3 ← 유일하게 0이 아님. 권고문 생성에 다양성 필요
- **Response format:** 일반 텍스트 (JSON 아님 — 권고문은 자연어)
- **외부 도구:** 없음
- **LangSmith:** `@traceable(name="insight_synthesizer")`
- **집계 로직:** Python으로 처리 (`_aggregate()`) — LLM 호출 없음

## RISEN

**Role:**
ASTE 결과를 집계하고 운영팀이 바로 활용할 수 있는 액션 권고문을 생성한다.

**Instructions:**
- 입력: reviews, aste_results, domain
- 집계: aspect별로 POS/NEG/NEU 카운트 + 비율 계산 (Python 로직, key = ASTEResult.aspect)
- LLM 호출: 집계 결과 → 구체적 운영 액션 권고문 생성
- 출력: aggregated_stats(dict), action_recommendations(str), final_report(str, JSON)
- final_report: aste_results + aggregated_stats + action_recommendations 통합 JSON

**Steps:**
1. aste_results에서 aspect별 감성 집계 (Python, LLM 호출 없음)
   - key: aspect (ASTEResult.aspect 문자열, ASTEResult에 category 필드 없음), value: `{"POS": n, "NEG": n, "NEU": n, "total": n, "neg_ratio": float}`
2. NEG 비율이 높은 상위 3개 aspect 추출
3. LLM 프롬프트 호출 → [P-05 참조](../design/prompt_spec.md#p-05-insight-synthesizer-프롬프트)
4. final_report JSON 조립
5. State 업데이트: aggregated_stats, action_recommendations, final_report

**Aggregation Logic:**
```python
from collections import defaultdict

def aggregate(aste_results: list) -> dict:
    stats = defaultdict(lambda: {"POS": 0, "NEG": 0, "NEU": 0, "total": 0})
    for t in aste_results:
        cat = t["aspect"]
        stats[cat][t["sentiment"]] += 1
        stats[cat]["total"] += 1
    for cat in stats:
        total = stats[cat]["total"]
        stats[cat]["neg_ratio"] = stats[cat]["NEG"] / total if total > 0 else 0.0
    return dict(stats)
```

**Expectation:**
```json
// aggregated_stats
{
  "요금": {"POS": 2, "NEG": 15, "NEU": 3, "total": 20, "neg_ratio": 0.75},
  "데이터_속도": {"POS": 8, "NEG": 5, "NEU": 2, "total": 15, "neg_ratio": 0.33}
}

// action_recommendations (자연어)
"1. 요금 관련 부정 감성 75% → 가성비 요금제 신설 또는 기존 요금제 혜택 강화 검토
 2. 데이터 속도 불만 33% → 혼잡 지역 네트워크 증설 우선순위 지정"

// final_report (JSON string)
{
  "domain": "telecom",
  "review_count": 20,
  "aste_results": [...],
  "aggregated_stats": {...},
  "action_recommendations": "...",
  "revisions_used": 2
}
```

**Narrowing:**
- aste_results, aspects, confidence, verdict 수정 금지
- action_recommendations에 "개선이 필요합니다" 같은 공허한 문장 금지
- 집계 수치 없이 권고문 작성 금지
- final_report는 반드시 JSON 직렬화 가능한 구조
