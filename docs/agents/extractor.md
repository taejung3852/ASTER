# Agent Spec: Aspect Extractor

## 도구 & LLM 설정
- **LLM:** `gemini-3.1-flash-lite` (via `langchain-google-genai`)
- **Temperature:** 0.0
- **Response format:** `application/json` (JSON mode 지원 확인됨)
- **외부 도구:**
  - GraphRAG (`src/retrieval/graphrag.py`) — aspect 공동출현 패턴 검색
  - Qdrant (`src/retrieval/vector_rag.py`) — 유사 리뷰 검색
- **LangSmith:** `@traceable(name="aspect_extractor")`
- **Context window:** 최대 1,048,576 tokens (입력 리뷰 배치 크기 사실상 무제한)

## RISEN

**Role:**
리뷰 배치에서 GraphRAG + Vector RAG 컨텍스트를 활용해 도메인 특화 aspect를 추출한다.

**Instructions:**
- 입력: reviews(List[str]), domain(str), graph_context(Optional[str]), vector_context(Optional[str])
- GraphRAG 검색: 리뷰 텍스트로 aspect 공동출현 그래프 탐색 → graph_context 생성
- Vector RAG 검색: Qdrant에서 유사 리뷰 top-k 검색 → vector_context 생성
- LLM 호출: 두 컨텍스트 + 리뷰 → aspect 목록 추출
- 도메인 taxonomy에 없는 aspect가 나오면 가장 가까운 카테고리로 정규화
- 출력 필드: aspects, graph_context, vector_context

**Steps:**
1. `retrieval/graphrag.py`로 graph_context 생성 (실패 시 None)
2. `retrieval/vector_rag.py`로 vector_context 생성 (실패 시 None)
3. LLM 프롬프트 호출 → [P-01 참조](../design/prompt_spec.md#p-01-aspect-extractor-프롬프트)
4. JSON 응답 파싱 → `List[Aspect]` 변환
5. State 업데이트: aspects, graph_context, vector_context

**Expectation:**
```json
{
  "aspects": [
    {"text": "요금", "category": "요금"},
    {"text": "데이터 속도", "category": "데이터_속도"},
    {"text": "고객센터 응대", "category": "고객_서비스"}
  ]
}
```

**Narrowing:**
- aste_results, confidence, verdict 필드 절대 수정 금지
- taxonomy 외 완전히 새로운 카테고리 생성 금지 (정규화로 처리)
- aspect가 0개면 ValueError raise
