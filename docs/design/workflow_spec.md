# 워크플로우 명세

## 노드-엣지 구조

```
[START]
   │
   ▼
[supervisor]
   │  초기 State 검증 + 도메인 확인
   │  → aspects=[], aste_results=[], revisions=0 등 기본값 보장
   │
   ▼
[aspect_extractor]
   │  GraphRAG: 리뷰 간 aspect 관계 패턴 검색
   │  Vector RAG: 유사 리뷰 검색 (Qdrant)
   │  LLM: 두 컨텍스트 + 리뷰 → aspects 추출
   │  → State: aspects, graph_context, vector_context
   │
   ▼
[sentiment_classifier]
   │  입력: reviews + aspects + graph_context + critic_feedback (revision 시)
   │  LLM: 각 aspect에 대한 ASTE 삼중 추출
   │  → State: aste_results, confidence
   │
   ▼
[critic]
   │  입력: reviews + aste_results + confidence
   │  LLM: 삼중 추출 품질 검증
   │  → State: verdict, critic_feedback, revisions+1
   │
   ├── verdict == "REVISE" AND revisions < max_revisions
   │      └──────────────────────────────→ [sentiment_classifier]
   │
   └── verdict == "PASS" OR revisions >= max_revisions
          │
          ▼
   [insight_synthesizer]
          │  입력: reviews + aste_results + aggregated_stats
          │  집계: aspect별 POS/NEG/NEU 카운트 + 비율
          │  LLM: 집계 결과 → 운영 액션 권고문 생성
          │  → State: aggregated_stats, action_recommendations, final_report
          │
          ▼
        [END]
```

## 조건부 라우팅 함수

```python
def route_after_critic(state: ABSAState) -> Literal["revise", "pass"]:
    if state["verdict"] == "REVISE" and state["revisions"] < state["max_revisions"]:
        return "revise"
    return "pass"
```

## 에이전트 담당 필드 매핑

| 에이전트 | 읽는 필드 | 쓰는 필드 |
|---|---|---|
| supervisor | reviews, domain | (기본값 주입) |
| aspect_extractor | reviews, domain | aspects, graph_context, vector_context |
| sentiment_classifier | reviews, aspects, graph_context, critic_feedback | aste_results, confidence |
| critic | reviews, aste_results, confidence | verdict, critic_feedback, revisions |
| insight_synthesizer | reviews, aste_results | aggregated_stats, action_recommendations, final_report |

## 에러 처리 정책

- LLM 파싱 실패 시: 해당 노드에서 예외 raise → LangGraph가 State를 오염시키지 않음
- Qdrant 연결 실패 시: vector_context = None으로 처리 후 진행 (Graceful degradation)
- GraphRAG 실패 시: graph_context = None으로 처리 후 진행
- max_revisions 도달 시: 현재 aste_results 그대로 synthesizer로 전달 (품질 경고 플래그 없음 — 향후 추가 가능)
