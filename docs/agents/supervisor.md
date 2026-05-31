# Agent Spec: Supervisor

## 도구 & LLM 설정
- **LLM:** 없음 (순수 Python 로직)
- **외부 도구:** 없음
- **LangSmith:** 트레이싱 불필요 (LLM 호출 없으므로)

## RISEN

**Role:**
ABSAState를 초기화하고 aspect_extractor로 워크플로우를 시작하는 오케스트레이터.
LLM 호출 없음 — 순수 Python 로직.

**Instructions:**
- 입력: reviews(List[str]), domain(str)
- 검증: reviews가 비어있으면 ValueError raise
- domain 유효성: "telecom" | "ecommerce" 외 값이면 ValueError
- 기본값 주입: aspects=[], aste_results=[], revisions=0, max_revisions=3,
  confidence=0.0, verdict="REVISE", critic_feedback=None,
  graph_context=None, vector_context=None,
  aggregated_stats={}, action_recommendations="", final_report=""

**Steps:**
1. reviews 비어있는지 확인
2. domain 유효성 확인
3. State에 기본값 필드 주입
4. 수정된 State 반환 (라우팅은 graph.py의 add_edge가 처리)

**Expectation:**
```python
# 입력
state = {"reviews": ["요금이 너무 비싸요"], "domain": "telecom"}

# 출력 (추가된 필드)
state = {
    "reviews": ["요금이 너무 비싸요"],
    "domain": "telecom",
    "aspects": [],
    "aste_results": [],
    "revisions": 0,
    "max_revisions": 3,
    "confidence": 0.0,
    "verdict": "REVISE",
    "critic_feedback": None,
    "graph_context": None,
    "vector_context": None,
    "aggregated_stats": {},
    "action_recommendations": "",
    "final_report": ""
}
```

**Narrowing:**
- LLM 호출 금지
- aspect_extractor 이외 노드로 라우팅 금지
- reviews 원문 수정 금지
