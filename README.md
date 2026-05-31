# ASTER

**A**spect **S**entiment **T**riple **E**xtraction with **R**etrieval

고객 리뷰 배치에서 ASTE(Aspect-Sentiment Triple Extraction)를 수행하고, 운영팀이 즉시 실행 가능한 액션 인사이트를 생성하는 LangGraph 기반 멀티에이전트 시스템.

---

## 개요

단순 긍/부정 분류(ABSA)에서 한 단계 나아가, `(aspect, opinion, sentiment)` 삼중 추출로 **"왜 부정인가"까지 설명**할 수 있도록 설계했다.

- **ASTE**: aspect별 opinion 표현과 sentiment를 함께 추출 → 설명 가능성 확보
- **GraphRAG**: 리뷰 간 aspect 공동출현 패턴으로 추출 정확도 향상
- **Vector RAG**: Qdrant 유사 리뷰 검색으로 컨텍스트 보강
- **Reflection 루프**: Critic → Classifier 피드백 사이클로 품질 자동 개선
- **LangSmith**: 전 노드 트레이싱으로 LLM 동작 관찰 가능

---

## 아키텍처

```
[입력: 리뷰 배치 + 도메인]
        │
        ▼
  [Supervisor]         입력 검증 + State 초기화 (LLM 없음)
        │
        ▼
[Aspect Extractor]     GraphRAG + Vector RAG → LLM → aspect 목록 추출
        │
        ▼
[Sentiment Classifier] aspect별 (opinion, sentiment, evidence) 추출
        │
        ▼
    [Critic]           PASS / REVISE 판정 (최대 3회 반복)
        │
   REVISE ──────────────────────────┐
        │                           │ (피드백 반영 재시도)
      PASS                          │
        │              ─────────────┘
        ▼
[Insight Synthesizer]  집계(Python) + 액션 권고문 생성(LLM)
        │
        ▼
[출력: aggregated_stats + action_recommendations + final_report]
```

---

## 기술 스택

| 항목 | 선택 | 이유 |
|---|---|---|
| 오케스트레이션 | LangGraph | Critic→Classifier 반복 루프(사이클) 구현 |
| LLM | Gemini 3.1 Flash Lite | 고빈도 경량 태스크 최적화, JSON mode 지원 |
| State | TypedDict | LangGraph 내부가 dict 기반 — Pydantic 변환 오버헤드 없음 |
| Vector DB | Qdrant | `:memory:`→운영 URL 한 줄 전환, payload 필터 지원 |
| Graph DB | networkx (MVP) | 빠른 프로토타이핑. Phase 2에서 GRAGLLM 논문 방식으로 교체 예정 |
| 트레이싱 | LangSmith | 노드별 LLM 입출력 관찰, 반복 횟수 모니터링 |

---

## 프로젝트 구조

```
ASTER/
├── main.py                  # 파이프라인 진입점
├── requirements.txt
├── .env.example
│
├── src/
│   ├── state.py             # ABSAState TypedDict 스키마
│   ├── graph.py             # StateGraph 조립 + 라우팅
│   ├── utils.py             # LLM 싱글턴 (llm_json / llm_text)
│   │
│   ├── agents/
│   │   ├── supervisor.py        # 입력 검증 + 기본값 주입
│   │   ├── extractor.py         # Aspect 추출
│   │   ├── classifier.py        # ASTE 삼중 추출
│   │   ├── critic.py            # PASS/REVISE 판정
│   │   └── synthesizer.py       # 집계 + 액션 권고문 생성
│   │
│   └── retrieval/
│       ├── graphrag.py          # networkx 공동출현 그래프
│       └── vector_rag.py        # Qdrant 유사 리뷰 검색
│
└── docs/
    ├── design/
    │   ├── state_definition.md  # ABSAState 스키마 명세
    │   ├── workflow_spec.md     # 노드-엣지 구조 명세
    │   ├── prompt_spec.md       # 프롬프트 템플릿 (P-01~P-05)
    │   └── decision_policy.md   # PASS/REVISE 기준 + 설계 결정 근거
    ├── agents/
    │   ├── supervisor.md
    │   ├── extractor.md
    │   ├── classifier.md
    │   ├── critic.md
    │   └── synthesizer.md
    └── conventions/
        ├── branch.md            # 브랜치 전략
        └── commit.md            # 커밋 메시지 컨벤션
```

---

## 시작하기

### 1. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일에 실제 키 입력:
```
GOOGLE_API_KEY=your_key
LANGCHAIN_API_KEY=your_key
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 실행

```bash
python main.py
```

---

## 출력 예시

```
=== ASTE 결과 ===
  [NEG] 요금 / 너무 비싸 (신뢰도: 0.92)
    근거: 원문: '요금이 너무 비싸서 해지를 고려하고 있어요'
  [POS] 데이터_속도 / 빠르다 (신뢰도: 0.88)
    근거: 원문: '5G 속도가 생각보다 훨씬 빠르네요'

=== 액션 권고 ===
1. 요금 관련 부정 감성 67% → 가성비 요금제 신설 또는 혜택 재설계 검토
2. 고객_서비스 불만 50% → 콜센터 대기 시간 단축 운영 방안 수립

=== 집계 통계 ===
  요금: NEG 66.7%
  고객_서비스: NEG 50.0%
```

---

## 도메인 지원

| 도메인 | Aspect 카테고리 |
|---|---|
| `telecom` | 요금, 데이터_속도, 통화_품질, 고객_서비스, 단말기, 부가서비스, 멤버십, 로밍, 인터넷, 개통_해지 |
| `ecommerce` | 배송, 품질, 가격, 고객_서비스, 포장, 환불_교환, 상품_설명, 결제, 앱_UI, 브랜드 |

---

## 설계 결정 핵심 포인트

**TypedDict를 선택한 이유**
LangGraph 내부는 dict 기반으로 State를 처리한다. Pydantic BaseModel을 쓰면 매 노드마다 `.model_dump()` / `.model_validate()` 변환이 필요하다. TypedDict는 런타임에 실제 dict이므로 마찰이 없고, 유효성 검사는 각 에이전트 노드 내부에서 직접 처리한다.

**Reflection 루프가 있어도 LangGraph를 쓰는 이유**
Critic → Classifier 피드백 사이클은 방향성 있는 사이클(cycle)이다. 단순 LangChain Chain으로는 이 사이클을 표현할 수 없고, LangGraph의 조건부 엣지(`add_conditional_edges`)가 있어야 `revisions < max_revisions` 조건으로 루프를 제어할 수 있다.

**강제 PASS 정책**
`revisions >= max_revisions`이면 Critic 판정과 무관하게 Synthesizer로 강제 진행한다. 배치 자동화 목적과 무한 루프 방지를 위한 설계. 향후 `low_confidence_items` 플래그로 해당 결과를 마킹해 사후 검토하는 방식으로 보완 예정.
