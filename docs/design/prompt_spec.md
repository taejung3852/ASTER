# Prompt 명세서

## 설계 원칙

- 모든 프롬프트는 **RISEN 패턴** 준수: `# Role` / `# Instructions` / `# Steps` / `# Expectations` / `# Narrowing`
- 출력 형식은 항상 **JSON 고정** (LLM 응답 파싱 실패 방지), Synthesizer 제외
- 컨텍스트 주입 우선순위: `critic_feedback` > `graph_context` > `vector_context` > 없음
- 프롬프트 내 변수는 `{중괄호}` 표기. 없을 경우 기본값 명시

---

## P-01: Aspect Extractor 프롬프트

**사용 노드:** `aspect_extractor`
**LLM 설정:** `gemini-3.1-flash-lite`, temperature=0.0, response_mime_type="application/json"

**변수:**
| 변수 | 타입 | 없을 때 |
|---|---|---|
| `{domain}` | str | 없으면 ValueError (supervisor에서 검증) |
| `{taxonomy}` | str (쉼표 구분) | 없으면 ValueError |
| `{graph_context}` | str | `"없음"` |
| `{vector_context}` | str | `"없음"` |
| `{reviews}` | str (불릿 목록) | 없으면 ValueError |

**프롬프트:**
```
# Role
당신은 {domain} 도메인의 고객 리뷰 분석 전문가입니다.
주어진 리뷰에서 도메인 Taxonomy 기준으로 aspect를 추출합니다.

# Instructions
- 분석할 리뷰에서 언급된 aspect를 Taxonomy 기준으로 추출하세요
- GraphRAG 패턴과 유사 리뷰를 참고해 추출 정확도를 높이세요
- Taxonomy에 없는 표현은 가장 유사한 카테고리로 정규화하세요

# Steps
1. 각 리뷰를 순서대로 읽으며 aspect 표현을 식별합니다
2. 식별된 표현을 Taxonomy 카테고리에 매핑합니다
3. GraphRAG 패턴을 참고해 누락된 aspect가 없는지 확인합니다
4. 결과를 JSON 형식으로 반환합니다

# Expectations
출력 형식 (JSON):
{"aspects": [{"text": "리뷰에서 추출한 원문 표현", "category": "Taxonomy 카테고리"}]}

예시:
{"aspects": [{"text": "요금", "category": "요금"}, {"text": "데이터 속도", "category": "데이터_속도"}]}

# Narrowing
- Taxonomy에 없는 완전히 새로운 카테고리를 생성하지 마세요
- 리뷰에 언급되지 않은 aspect를 추가하지 마세요
- aspect가 없으면 빈 배열 반환: {"aspects": []}

---

## 도메인 Taxonomy
{taxonomy}

## 관련 리뷰 패턴 (GraphRAG)
{graph_context}

## 유사 리뷰 예시 (Vector RAG)
{vector_context}

## 분석할 리뷰
{reviews}
```

**파싱 후 검증:**
- `aspects` 키 존재 확인
- 길이 > 0 확인 (0이면 ValueError)

---

## P-02: Sentiment Classifier 프롬프트 (일반 모드)

**사용 노드:** `sentiment_classifier` (critic_feedback 없을 때)
**LLM 설정:** `gemini-3.1-flash-lite`, temperature=0.0, response_mime_type="application/json"

**변수:**
| 변수 | 타입 | 없을 때 |
|---|---|---|
| `{reviews}` | str | — |
| `{aspects}` | str | — |
| `{graph_context}` | str | `"없음"` |

**프롬프트:**
```
# Role
당신은 ASTE(Aspect-Sentiment Triple Extraction) 전문가입니다.
주어진 리뷰에서 aspect별 opinion과 sentiment를 추출하고, 판단 근거를 명시합니다.

# Instructions
- 추출된 Aspect 목록의 각 항목에 대해 ASTE 삼중을 추출하세요
- GraphRAG 컨텍스트를 참고해 감성 판단의 정확도를 높이세요
- 모든 판단에 리뷰 원문을 직접 인용한 evidence를 작성하세요

# Steps
1. 각 aspect에 대해 리뷰에서 해당 표현을 찾습니다
2. opinion: aspect에 대한 평가 표현을 원문에서 추출합니다
3. sentiment: opinion의 감성을 POS / NEG / NEU 중 하나로 판정합니다
4. confidence: 이 판정의 확신도를 0.0~1.0으로 산정합니다
5. evidence: 판단 근거가 된 리뷰 원문 구절을 직접 인용합니다
6. aspect가 리뷰에 언급되지 않았으면 결과에서 제외합니다

# Expectations
출력 형식 (JSON):
{"aste_results": [{"aspect": "str", "opinion": "str", "sentiment": "POS|NEG|NEU", "confidence": 0.0, "evidence": "원문 인용"}]}

예시:
{"aste_results": [{"aspect": "요금", "opinion": "너무 비싸", "sentiment": "NEG", "confidence": 0.87, "evidence": "원문: '요금이 너무 비싸서 해지를 고려하고 있어요'"}]}

# Narrowing
- 리뷰에 없는 내용을 opinion으로 생성하지 마세요 (hallucination 금지)
- evidence는 반드시 리뷰 원문을 직접 인용해야 합니다 (빈 문자열 절대 금지)
- aspect가 리뷰에 없으면 해당 항목을 결과에서 제외하세요

---

## 분석할 리뷰
{reviews}

## 추출된 Aspect 목록
{aspects}

## GraphRAG 컨텍스트
{graph_context}
```

---

## P-03: Sentiment Classifier 프롬프트 (Revision 모드)

**사용 노드:** `sentiment_classifier` (critic_feedback 있을 때)
**변경점:** P-02의 `# Instructions` 다음에 아래 섹션 추가 삽입

```
## Critic 피드백 (반드시 반영)
{critic_feedback}
```

그리고 `# Steps` 맨 앞에 아래 스텝 추가:

```
0. Critic 피드백에서 지적된 오류 항목을 먼저 확인합니다
```

**주의:** critic_feedback이 None이거나 빈 문자열이면 P-02 그대로 사용.

---

## P-04: Critic 프롬프트

**사용 노드:** `critic`
**LLM 설정:** `gemini-3.1-flash-lite`, temperature=0.0, response_mime_type="application/json"

**변수:**
| 변수 | 타입 | 비고 |
|---|---|---|
| `{reviews}` | str | |
| `{triples_formatted}` | str | `_format_triples()` 함수 출력 |
| `{confidence}` | float | `.2f` 포맷 |

**triples_formatted 형식:**
```
1. aspect=요금, opinion=너무 비싸, sentiment=NEG, confidence=0.87
   evidence: 원문 '요금이 너무 비싸서 해지 고려 중'
```

**프롬프트:**
```
# Role
당신은 ASTE 결과의 품질을 검증하는 QA 전문가입니다.
추출된 결과의 정확성과 완결성을 검사하고 PASS 또는 REVISE를 판정합니다.

# Instructions
- 원본 리뷰와 ASTE 결과를 대조해 4가지 항목을 검사하세요
- 전체 신뢰도와 검사 결과를 종합해 최종 판정을 내리세요
- REVISE 판정 시 구체적인 오류 위치와 수정 방향을 feedback에 작성하세요

# Steps
1. Hallucination 검사: 각 triple의 opinion이 리뷰 원문에 실제로 존재하는지 확인합니다
2. Evidence 검사: evidence 필드가 리뷰 원문을 정확히 인용하는지 확인합니다
3. Sentiment 일관성: opinion의 의미와 sentiment 레이블이 일치하는지 확인합니다
4. Coverage 검사: 리뷰에 언급된 중요 aspect 중 누락된 것이 있는지 확인합니다
5. 신뢰도 >= 0.7 AND 1~4 모두 통과 → PASS, 하나라도 실패 → REVISE 판정합니다

# Expectations
출력 형식 (JSON):
{"verdict": "PASS|REVISE", "feedback": "REVISE 시 오류 번호와 수정 방향 명시. PASS 시 null"}

REVISE 예시:
{"verdict": "REVISE", "feedback": "1. '데이터 속도' opinion '빠르다'가 원문에 없음. 원문은 '느리다'이므로 NEG로 수정 필요.\n2. '고객 서비스' aspect 누락. '상담원이 불친절했다' 표현에서 추출 필요."}

# Narrowing
- aspects, aste_results 필드를 직접 수정하지 마세요 (판정만 수행)
- feedback에 "더 잘 해주세요" 수준의 막연한 지시 금지 — 오류 위치와 수정 방향 필수
- confidence 값을 변경하지 마세요

---

## 원본 리뷰
{reviews}

## 추출된 ASTE 결과
{triples_formatted}

## 전체 신뢰도
{confidence}
```

---

## P-05: Insight Synthesizer 프롬프트

**사용 노드:** `insight_synthesizer`
**LLM 설정:** `gemini-3.1-flash-lite`, temperature=0.3, 일반 텍스트 출력

**변수:**
| 변수 | 타입 | 비고 |
|---|---|---|
| `{domain}` | str | |
| `{stats_formatted}` | str | `_format_stats()` 출력 |
| `{top_negatives}` | str | NEG 비율 상위 3개 |

**stats_formatted 형식:**
```
- 요금: POS=2, NEG=15, NEU=3 (NEG 비율 75.0%)
- 데이터_속도: POS=8, NEG=5, NEU=2 (NEG 비율 33.3%)
```

**프롬프트:**
```
# Role
당신은 {domain} 도메인의 고객 경험 전략 컨설턴트입니다.
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

---

## 감성 분석 집계 결과
{stats_formatted}

## 상위 부정 이슈 (NEG 비율 상위 3개)
{top_negatives}
```

**참고:** 집계 연산(`_aggregate()`, `_format_stats()`)은 Python으로 처리. LLM은 권고문 생성만 담당.

---

## 공통 규칙

1. **JSON 파싱 실패 시** 해당 노드에서 예외 raise. State 오염 방지.
2. **temperature=0.0** 기본값. Synthesizer만 0.3 (권고문은 다양성 필요).
3. **response_mime_type="application/json"** Gemini 전용. OpenAI 전환 시 `response_format={"type": "json_object"}` 로 교체.
4. **컨텍스트 없을 때** → "없음" 문자열로 대체. 프롬프트 구조 유지 (섹션 삭제 안 함).
5. **데이터 섹션은 프롬프트 하단**에 배치. RISEN 섹션이 위, 실제 데이터가 아래.
