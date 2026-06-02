# ABSAState 스키마 정의

상세 구현은 [`src/state.py`](../../src/state.py)를 참조한다.

---

## 설계 원칙

모든 에이전트는 `ABSAState`를 통해서만 데이터를 주고받는다. 각 에이전트는 자신의 담당 필드만 반환하고, LangGraph가 기존 State에 merge한다. 담당 필드 외를 건드리면 다른 에이전트의 결과를 덮어쓰는 버그가 된다.

---

## 필드 정의

### 입력 필드

| 필드 | 타입 | 초기값 | 설명 |
|---|---|---|---|
| `reviews` | `List[str]` | 외부 주입 | 처리할 리뷰 배치 |
| `domain` | `Literal["telecom", "ecommerce"]` | 외부 주입 | 도메인. `DOMAIN_TAXONOMY` 키와 매핑되어 aspect 통제 어휘 결정 |

### Extractor 출력 필드

| 필드 | 타입 | 초기값 | 설명 |
|---|---|---|---|
| `aspects` | `List[Aspect]` | — | 추출된 aspect 목록. `Aspect = {text: str, category: str}` |
| `graph_context` | `Optional[str]` | `None` | GraphRAG 검색 결과. Classifier 프롬프트에 컨텍스트로 주입 |
| `vector_context` | `Optional[str]` | `None` | Qdrant 유사 리뷰 검색 결과. 마찬가지로 프롬프트 컨텍스트용 |

`graph_context`와 `vector_context`는 검색 실패 시 `None`을 유지하고 파이프라인이 계속 진행된다 (graceful degradation). 없으면 프롬프트에 "없음"으로 주입된다.

### Classifier 출력 필드

| 필드 | 타입 | 초기값 | 설명 |
|---|---|---|---|
| `aste_results` | `List[ASTEResult]` | — | ASTE 트리플 추출 결과. Critic의 검토 대상이자 Synthesizer의 집계 입력 |
| `confidence` | `float` | — | `aste_results` 전체의 평균 신뢰도 (0.0~1.0). Critic이 PASS/REVISE 판정에 참고 |

`ASTEResult` 구조: `{review_index, aspect, opinion, sentiment, confidence, evidence}`. `evidence`는 빈 문자열 불가 — 설명 가능성(explainability)의 물리적 구현체다.

### Critic 판정 필드

| 필드 | 타입 | 초기값 | 설명 |
|---|---|---|---|
| `verdict` | `Literal["PASS", "REVISE"]` | — | Critic의 판정. 라우팅 함수 `_route_after_critic`이 읽어 다음 노드를 결정 |
| `revisions` | `int` | `0` (supervisor 주입) | 현재까지 재시도한 횟수. Critic이 REVISE 판정 시마다 +1 |
| `max_revisions` | `int` | `3` (supervisor 주입) | 재시도 상한. `revisions >= max_revisions`이면 REVISE여도 Classifier로 돌아가지 않음 |
| `critic_feedback` | `Optional[str]` | `None` | Critic이 Classifier에 전달하는 피드백. REVISE 시 Classifier 프롬프트에 주입됨 |

### HITL 대기열 필드

| 필드 | 타입 | 초기값 | 설명 |
|---|---|---|---|
| `low_confidence_items` | `List[ASTEResult]` | `[]` (supervisor 주입) | `revisions >= max_revisions` 시 `aste_results`를 이곳으로 이동. Synthesizer는 이 필드를 집계에서 제외하므로 낮은 품질의 결과가 최종 리포트에 섞이지 않음. 사람이 사후에 꺼내 검토하는 용도 |

`aste_results` → `low_confidence_items` 이동은 `hitl_triage` 노드가 담당한다. 이동 후 `aste_results`는 비워진다.

### Synthesizer 출력 필드

| 필드 | 타입 | 초기값 | 설명 |
|---|---|---|---|
| `aggregated_stats` | `dict` | `{}` (supervisor 주입) | aspect별 감성 집계. 구조는 아래 참조 |
| `action_recommendations` | `str` | — | NEG 비율 높은 순으로 정렬된 운영 액션 권고문 (자연어) |
| `final_report` | `str` | — | 집계 통계 + 권고문을 담은 최종 리포트 (JSON 직렬화) |

`aggregated_stats` 구조:
```python
{
    "요금": {"POS": 2, "NEG": 8, "NEU": 1, "total": 11, "neg_ratio": 0.727},
    "데이터_속도": {"POS": 5, "NEG": 3, "NEU": 2, "total": 10, "neg_ratio": 0.3},
}
```
이 딕셔너리는 텍스트로 변환되어 LLM에 주입(`action_recommendations` 생성)되고, 동시에 State에 구조화 데이터로 보존된다.

---

## 에이전트별 필드 접근 요약

| 필드 | 초기화 | 쓰기 | 읽기 |
|---|---|---|---|
| `reviews` | 외부 입력 | — | extractor |
| `domain` | 외부 입력 | — | supervisor(검증), extractor, vector_rag |
| `aspects` | — | extractor | — |
| `graph_context` | — | extractor | classifier |
| `vector_context` | — | extractor | classifier |
| `aste_results` | — | classifier, hitl_triage(비움) | critic, synthesizer |
| `confidence` | — | classifier | critic |
| `verdict` | — | critic | `_route_after_critic` |
| `revisions` | `0` (supervisor) | critic (+1) | critic, `_route_after_critic` |
| `max_revisions` | `3` (supervisor) | — | critic, `_route_after_critic` |
| `critic_feedback` | — | critic | classifier |
| `low_confidence_items` | `[]` (supervisor) | hitl_triage | — (사람 검토용) |
| `aggregated_stats` | `{}` (supervisor) | synthesizer | synthesizer(내부) |
| `action_recommendations` | — | synthesizer | synthesizer(내부) |
| `final_report` | — | synthesizer | — |

---

## DOMAIN_TAXONOMY

`state.py`에 정의된 도메인별 통제 어휘(controlled vocabulary)다.

```python
DOMAIN_TAXONOMY = {
    "telecom":    ["요금", "데이터_속도", "통화_품질", ...],
    "ecommerce":  ["배송", "품질", "가격", ...],
}
```

**키(domain명)**: supervisor가 입력 검증에 사용. `domain not in DOMAIN_TAXONOMY`이면 즉시 예외.

**값(aspect 리스트)**: extractor 프롬프트에 직접 주입되어 LLM이 aspect를 이 목록으로 정규화하도록 유도. 없으면 "요금"/"가격"/"비용"이 전부 다른 aspect로 추출되어 집계가 무의미해진다.

새 도메인을 지원하려면 `DOMAIN_TAXONOMY`에 키-값 쌍을 추가하고 `domain` 필드의 `Literal` 타입도 함께 확장한다.

---

## State 흐름

```
START
  ↓ reviews, domain 주입
supervisor          → revisions=0, max_revisions=3, low_confidence_items=[], aggregated_stats={} 초기화
  ↓
aspect_extractor    → aspects, graph_context, vector_context 채움
  ↓
sentiment_classifier → aste_results, confidence 채움
  ↓
critic              → verdict 결정, critic_feedback 기록, revisions +1
  ├── REVISE + revisions < max_revisions  → sentiment_classifier (재시도)
  ├── REVISE + revisions >= max_revisions → hitl_triage
  └── PASS                                → insight_synthesizer
hitl_triage         → aste_results → low_confidence_items 이동
  ↓
insight_synthesizer → aggregated_stats, action_recommendations, final_report 채움
END
```

---

## 불변 규칙

1. `revisions >= max_revisions`이면 REVISE 판정 시 `hitl_triage`를 거쳐 `low_confidence_items`에 저장 후 `insight_synthesizer`로 전진
2. 에이전트는 자신의 담당 필드만 업데이트한다 (위 테이블의 "쓰기" 열 참조)
3. `aste_results`의 모든 항목에 `evidence` 필드 필수. 빈 문자열 허용 안 됨
