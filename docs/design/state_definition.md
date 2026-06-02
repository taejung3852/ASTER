# ABSAState 스키마 정의

## 설계 원칙

- 모든 에이전트는 `ABSAState`를 통해서만 데이터를 주고받는다
- `evidence` 필드: 설명 가능성(explainability) 측정의 핵심. 에이전트가 판단 근거를 반드시 자연어로 기록
- `critic_feedback`: Reflection 루프에서 Classifier로 역전파되는 피드백. State에 누적 기록
- `revisions`: 무한 루프 방지. `max_revisions` 초과 시 hitl_triage 경유 → low_confidence_items 저장

## 확정 스키마

```python
from typing import TypedDict, Literal, List, Optional
import operator

class Aspect(TypedDict):
    text: str          # 추출된 aspect 원문 ("요금", "데이터 속도" 등)
    category: str      # 정규화된 카테고리 (아래 도메인별 taxonomy 참조)

class ASTEResult(TypedDict):
    review_index: int  # 추출 원본 리뷰의 0-based 인덱스
    aspect: str        # aspect 원문
    opinion: str       # opinion 원문
    sentiment: Literal["POS", "NEG", "NEU"]
    confidence: float  # 0.0 ~ 1.0
    evidence: str      # 판단 근거 자연어 설명 (설명 가능성 핵심)

class ABSAState(TypedDict):
    # ── 입력 ──────────────────────────────────────────────
    reviews: List[str]                     # 처리할 리뷰 배치
    domain: Literal["telecom", "ecommerce"]  # 도메인 (aspect taxonomy 선택)

    # ── Extractor 출력 ─────────────────────────────────────
    aspects: List[Aspect]                  # 추출된 aspect 목록
    graph_context: Optional[str]           # GraphRAG 검색 결과 (프롬프트 컨텍스트용)
    vector_context: Optional[str]          # Qdrant 유사 리뷰 검색 결과

    # ── Classifier 출력 ────────────────────────────────────
    aste_results: List[ASTEResult]         # ASTE 삼중 추출 결과
    confidence: float                      # 전체 배치 평균 신뢰도 (aste_results 기반 평균)

    # ── Critic 판정 ────────────────────────────────────────
    verdict: Literal["PASS", "REVISE"]
    revisions: int                         # 현재 revision 횟수
    max_revisions: int                     # 기본값 3 (graph 생성 시 주입)
    critic_feedback: Optional[str]         # Classifier에 전달할 피드백

    # ── HITL 대기열 ────────────────────────────────────────
    low_confidence_items: List[ASTEResult] # max_revisions 초과 시 사람 검토용

    # ── Synthesizer 출력 ───────────────────────────────────
    aggregated_stats: dict                 # aspect별 감성 집계 통계
    action_recommendations: str            # 운영 액션 권고문 (자연어)
    final_report: str                      # 최종 구조화 리포트 (JSON 직렬화)
```

## 도메인별 Aspect Taxonomy

### telecom
```
요금, 데이터_속도, 통화_품질, 고객_서비스, 단말기, 부가서비스, 멤버십, 로밍, 인터넷, 개통_해지
```

### ecommerce
```
배송, 품질, 가격, 고객_서비스, 포장, 환불_교환, 상품_설명, 결제, 앱_UI, 브랜드
```

## State 흐름 요약

```
START
  ↓ reviews, domain 주입
supervisor
  ↓ (라우팅만, State 변경 없음)
aspect_extractor
  ↓ aspects, graph_context, vector_context 채움
sentiment_classifier
  ↓ aste_results, confidence 채움
critic
  ↓ verdict 결정, critic_feedback 기록, revisions++ 
  ├── REVISE + revisions < max_revisions → sentiment_classifier (재시도)
  ├── REVISE + revisions >= max_revisions → hitl_triage (HITL 대기열 저장)
  └── PASS  → insight_synthesizer
hitl_triage
  ↓ low_confidence_items 저장
insight_synthesizer
  ↓ aggregated_stats, action_recommendations, final_report 채움
END
```

## 불변 규칙

1. `revisions >= max_revisions`이면 REVISE 판정 시 `hitl_triage`를 거쳐 `low_confidence_items`에 저장 후 `insight_synthesizer`로 전진 (사람 검토 대기)
2. 에이전트는 자신의 담당 필드만 업데이트한다 (다른 필드 덮어쓰기 금지)
3. `aste_results`의 모든 항목에 `evidence` 필드 필수. 빈 문자열 허용 안 됨
