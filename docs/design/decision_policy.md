# Decision Policy

## 1. Critic 판정 기준

### PASS 조건 (AND)
```
confidence >= 0.7
AND hallucination 없음 (opinion이 리뷰 원문에 존재)
AND evidence가 원문을 정확히 인용
AND sentiment-opinion 일관성 통과
AND 주요 aspect 누락 없음
```

### REVISE 조건 (OR)
```
confidence < 0.7
OR hallucination 감지
OR evidence 부정확
OR sentiment-opinion 불일치
OR 주요 aspect 누락
```

### 강제 전진 (Critic 판정 무시)
```
REVISE + revisions >= max_revisions → hitl_triage 노드 경유
```
이유: 무한 루프 방지. 품질보다 시스템 안정성 우선.
해당 결과는 `low_confidence_items`에 저장되어 사람이 사후 검토할 수 있도록 분리 보관.

---

## 2. confidence 임계값 0.7 설정 근거

| 임계값 | 문제 |
|---|---|
| 0.9 이상 | Revision 과다 발생. max_revisions 소진 후 저품질 결과 양산 |
| 0.5 이하 | 검증 기능 무력화. Critic이 있으나 마나 |
| **0.7** | 중간값. 실제 운영 후 LangSmith 데이터 보고 조정 예정 |

→ **0.7은 초기값이지 고정값이 아니다.** 벤치마크 후 조정.

---

## 3. max_revisions = 3 설정 근거

| 값 | 문제 |
|---|---|
| 1 | Reflection 의미 없음. 한 번 틀리면 바로 강제 PASS |
| 5 이상 | 토큰 비용 급증. 배치 처리 속도 저하 |
| **3** | AutoDoc-MAS 실험값. 3회면 수렴하거나 수렴 불가 판별 가능 |

---

## 4. 라우팅 결정 함수

```python
def _route_after_critic(state: ABSAState) -> Literal["revise", "pass", "triage"]:
    if state["verdict"] == "PASS":
        return "pass"
    if state["revisions"] < state["max_revisions"]:
        return "revise"
    return "triage"  # REVISE + max_revisions 소진 → HITL 대기열
```

**중요:** `revisions >= max_revisions`이면 verdict가 "REVISE"여도 `triage` 반환.
Critic의 판정보다 revisions 카운터가 우선권을 가지며, 해당 결과는 `low_confidence_items`로 분리된다.

---

## 5. Graceful Degradation 정책

| 장애 상황 | 처리 방식 | 이유 |
|---|---|---|
| GraphRAG 검색 실패 | `graph_context = None` 후 진행 | Vector RAG만으로도 동작 가능 |
| Qdrant 검색 실패 | `vector_context = None` 후 진행 | LLM 자체 지식으로 fallback |
| 둘 다 실패 | 컨텍스트 없이 LLM 단독 진행 | 기능 저하이나 시스템 중단 없음 |
| LLM JSON 파싱 실패 | 해당 노드 예외 raise | State 오염보다 명시적 실패가 낫다 |
| aspect 0개 추출 | ValueError raise | 빈 배열로 계속하면 후속 노드 전체 무의미 |

---

## 6. Supervisor 검증 정책

Supervisor는 LLM 없이 아래 두 조건만 검사:

```python
# 조건 1
if not state.get("reviews"):
    raise ValueError("reviews는 비어있을 수 없습니다")

# 조건 2
if state.get("domain") not in DOMAIN_TAXONOMY:
    raise ValueError(f"domain은 {list(DOMAIN_TAXONOMY.keys())} 중 하나")
```

이 외 검증은 각 에이전트 노드 책임. Supervisor는 게이트키퍼 역할만.

---

## 7. evidence 필드 정책

- 모든 ASTEResult에 evidence 필수
- 빈 문자열("") 허용 안 됨
- evidence 없는 triple이 파싱되면 → classifier 노드에서 ValueError raise
- confidence를 낮추더라도 evidence는 반드시 작성

이유: evidence가 없으면 설명 가능성 지표(LangSmith LLM-as-judge) 측정 불가.

---

## 8. 향후 추가 예정 정책

### low_confidence 대기열 (구현 완료)
max_revisions 소진 후 REVISE 판정된 항목을 `hitl_triage` 노드에서 분리 보관.

```python
# ABSAState 필드 (구현됨)
"low_confidence_items": List[ASTEResult]  # 사람 검토 대기 결과 목록
```

### 도메인 자동 감지 (미구현)
현재 domain을 사용자가 명시적으로 입력. 추후 리뷰 텍스트에서 도메인 자동 추론 기능 추가 가능.
