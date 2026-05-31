# Agent Spec: Sentiment Classifier

## 도구 & LLM 설정
- **LLM:** `gemini-3.1-flash-lite` (via `langchain-google-genai`)
- **Temperature:** 0.0
- **Response format:** `application/json`
- **외부 도구:** 없음 (Extractor가 만든 graph_context를 State에서 읽음)
- **LangSmith:** `@traceable(name="sentiment_classifier")`
- **Revision 모드:** critic_feedback 존재 시 P-03 프롬프트로 자동 전환

## RISEN

**Role:**
추출된 aspect에 대해 opinion과 sentiment를 결합한 삼중 추출을 수행한다.
Critic의 피드백이 있으면 반드시 반영해서 재시도한다.

**Instructions:**
- 입력: reviews, aspects, graph_context, critic_feedback(Optional[str])
- critic_feedback != None이면 revision 모드: 이전 실수를 고쳐야 함
- 각 aspect에 대해 (aspect, opinion, sentiment, confidence, evidence) 추출
- confidence: 개별 추출의 확신도 (0.0~1.0)
- evidence: 해당 판단의 근거가 된 리뷰 원문 구절 인용 필수
- 출력 필드: aste_results, confidence (전체 배치 평균)

**Steps:**
1. critic_feedback 여부 확인 → 있으면 revision 모드
2. LLM 프롬프트 호출 → [P-02 (일반)](../design/prompt_spec.md#p-02-sentiment-classifier-프롬프트-일반-모드) / [P-03 (revision)](../design/prompt_spec.md#p-03-sentiment-classifier-프롬프트-revision-모드)
3. JSON 파싱 → `List[Triple]` 변환
4. 전체 confidence = mean([t["confidence"] for t in triples])
5. State 업데이트: aste_results, confidence

**Expectation:**
```json
{
  "aste_results": [
    {
      "aspect": "요금",
      "opinion": "너무 비싸",
      "sentiment": "NEG",
      "confidence": 0.87,
      "evidence": "리뷰 원문: '요금이 너무 비싸서 해지를 고려하고 있어요'"
    }
  ]
}
```

**Narrowing:**
- aspects 필드 수정 금지
- graph_context, vector_context 수정 금지
- evidence 빈 문자열 절대 금지 — confidence를 낮추더라도 근거 작성 필수
- 리뷰에 없는 내용을 opinion으로 지어내지 말 것
