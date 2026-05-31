# Agent Spec: Critic

## 도구 & LLM 설정
- **LLM:** `gemini-3.1-flash-lite` (via `langchain-google-genai`)
- **Temperature:** 0.0
- **Response format:** `application/json`
- **외부 도구:** 없음
- **LangSmith:** `@traceable(name="critic")`
- **판정 임계값:** confidence >= 0.7 → PASS ([decision_policy.md](../design/decision_policy.md) 참조)

## RISEN

**Role:**
Classifier의 추출 결과를 검증하고 PASS/REVISE를 판정한다.
REVISE 시 구체적인 수정 지시를 critic_feedback에 기록한다.
(AutoDoc-MAS Reflection 루프 패턴 동일하게 적용)

**Instructions:**
- 입력: reviews, aste_results, confidence, revisions, max_revisions
- 검증 항목:
  1. 모든 추출 결과에 evidence가 있는가
  2. opinion이 리뷰 원문에 실제로 존재하는가 (hallucination 검사)
  3. sentiment가 opinion과 논리적으로 일치하는가
  4. 중요한 aspect가 누락되지 않았는가
- PASS 조건: confidence >= 0.7 AND 위 검증 항목 문제 없음
- REVISE 조건: confidence < 0.7 OR 검증 항목 실패
- revisions >= max_revisions이면 verdict와 무관하게 graph.py의 라우터가 강제 PASS 처리
- 출력 필드: verdict, critic_feedback, revisions(+1)

**Steps:**
1. confidence 임계값 확인 (0.7)
2. aste_results를 `_format_triples()` 로 포매팅 후 LLM 프롬프트 호출 → [P-04 참조](../design/prompt_spec.md#p-04-critic-프롬프트)
3. 판정 결정: PASS / REVISE
4. REVISE 시 구체적 오류 목록 + 수정 방향을 critic_feedback에 작성
5. revisions += 1
6. State 업데이트: verdict, critic_feedback, revisions

**Expectation (REVISE):**
```json
{
  "verdict": "REVISE",
  "feedback": "1. '데이터 속도' aspect의 opinion '빠르다'가 원문에 없음 (hallucination). 원문에는 '느린 것 같다'로 표현됨. NEG로 수정 필요.\n2. '고객 서비스' aspect 누락. 원문 '상담원이 불친절했다'에서 추출 필요."
}
```

**Expectation (PASS):**
```json
{
  "verdict": "PASS",
  "feedback": null
}
```

**Narrowing:**
- aspects, aste_results 수정 금지 (판정만 수행)
- confidence 수정 금지
- revisions는 반드시 기존 값 +1 (초기화나 감소 금지)
- critic_feedback에 막연한 "더 잘 해주세요" 수준 금지 — 구체적 오류 위치와 수정 방향 필수
