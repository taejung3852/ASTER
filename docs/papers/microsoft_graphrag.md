# Microsoft GraphRAG

> arXiv:2404.16130 | "From Local to Global: A GraphRAG Approach to Query-Focused Summarization"
> Darren Edge et al., Microsoft Research (2024)

---

## Abstract

기존 RAG가 풀지 못하는 문제가 있다. "이 데이터셋의 주요 테마가 뭐야?" 같은 질문이다. 쿼리와 유사한 문서 조각을 찾는 방식은 로컬 사실 검색엔 강하지만, 전체 코퍼스를 조망해야 하는 글로벌 질문엔 구조적으로 한계가 있다. GraphRAG는 이 간극을 LLM 기반 지식 그래프와 커뮤니티 요약을 결합해 메운다. 인덱싱 단계에서 LLM으로 엔티티 그래프를 만들고, 그래프를 커뮤니티로 분할해 커뮤니티별 요약을 미리 생성해 둔다. 쿼리가 들어오면 이 요약들을 map-reduce로 순회해 최종 답변을 만든다. 실험에서는 포괄성(comprehensiveness)과 다양성(diversity) 기준으로 기존 벡터 RAG 대비 72~83% 승률을 보였다.

---

## Section 1: Introduction

논문이 겨냥하는 문제는 "sensemaking"이다. 방대한 텍스트에서 전체적인 패턴이나 테마를 파악하는 것, 즉 로컬 사실이 아니라 데이터셋 전체를 이해하는 질문이다. 벡터 RAG는 이런 질문에 본질적으로 약하다. 쿼리와 가까운 문서 조각만 꺼내다 보니 전체 맥락을 잃는다.

GraphRAG의 동작 흐름은 네 단계다. LLM으로 지식 그래프를 구성하고, 그래프를 계층적 커뮤니티로 분할하고, 커뮤니티별 요약을 bottom-up으로 생성한 뒤, 쿼리 시 map-reduce로 부분 답변들을 통합한다. 평가는 LLM-as-a-judge 방식을 사용했다.

---

## Section 2: Background

### RAG의 계보와 GraphRAG의 위치

전통적인 벡터 RAG는 임베딩 유사도로 청크를 검색한다. GraphRAG는 여기에 "self-memory"(사전 생성 요약) 개념과 계층적 요약 집계를 더한 뒤, 그래프 커뮤니티 탐지를 얹은 구조다. 기존 연구에서 그래프의 모듈성(modularity)을 이런 방식으로 활용한 사례는 없었다.

### 평가 방법론

기존 벤치마크는 로컬 사실 검색 평가용이라 글로벌 센스메이킹 평가에 쓸 수 없다. 그래서 논문은 LLM이 페르소나 기반으로 질문을 자동 생성하는 Adaptive benchmarking을 택했다. 평가 기준은 네 가지다: Comprehensiveness(포괄성), Diversity(다양성), Empowerment(정보 충분성), Directness(간결성). 마지막 항목인 Directness는 나중에 벡터 RAG가 GraphRAG를 역으로 이기는 기준이 된다.

---

## Section 3: Methods

### 3.1.1 소스 문서 → 텍스트 청크

600 토큰 단위, 100 토큰 오버랩으로 분할한다. 청크 크기가 커지면 LLM 호출 횟수는 줄지만 앞부분 recall이 떨어지는 trade-off가 있다.

### 3.1.2 텍스트 청크 → 엔티티 & 관계 추출

ASTER가 가장 직접적으로 차용할 부분이다. LLM 프롬프트로 세 가지를 추출한다. 엔티티는 이름·타입·설명, 관계는 소스-타겟·설명·강도 점수(1~10), 클레임은 검증 가능한 사실 문장이다. 예를 들어 "Quantum Systems → NeoChip, 2016년 인수, 강도=9" 같은 형태다. 도메인 특화 few-shot 예시로 추출 품질을 높일 수 있고, Self-reflection 기법으로 누락된 엔티티를 보완한다. 청크가 클수록 LLM이 엔티티를 놓치기 쉬워서, "놓친 엔티티를 더 찾아라"는 재호출로 recall을 높이는 것이다.

### 3.1.3~3.1.4 지식 그래프 → 그래프 커뮤니티

엔티티 인스턴스들을 노드로 통합하고, 관계의 중복 횟수를 엣지 가중치로 쓴다. 커뮤니티 탐지에는 Leiden 알고리즘을 사용한다. Louvain(2008)의 개선판으로, Louvain이 연결되지 않은 커뮤니티를 만들 수 있는 문제를 해결한 버전이다. 결과적으로 모든 노드가 상호 배타적이고 완전하게 커뮤니티에 속하게 된다.

### 3.1.5~3.1.6 커뮤니티 요약 → 글로벌 답변

Leaf 레벨에서는 노드·엣지·클레임 설명을 degree 순으로 채워 요약하고, 상위 레벨에서는 서브커뮤니티 요약을 재귀적으로 집계한다. 쿼리가 오면 커뮤니티 요약들을 랜덤 셔플 후 청크 분할하고, 각 청크에서 부분 답변과 도움도 점수(0~100)를 뽑은 뒤(Map), 점수 내림차순으로 쌓아 최종 답변을 만든다(Reduce).

---

## Section 4~5: Results

실험은 두 데이터셋(Podcast 전사 ~100만 토큰, 뉴스 기사 ~170만 토큰)으로 진행했다. 결과는 GraphRAG가 포괄성과 다양성에서 벡터 RAG 대비 72~83% 승률을 보였다. 그래프 없이 요약만 쓰는 TS(Text Summarization) 대비로도 57~64% 승률이다. 다만 Directness(간결성)에서는 벡터 RAG가 역으로 이긴다. GraphRAG가 포괄적으로 답하다 보니 답변이 길어지는 trade-off다. 토큰 효율 면에서는 루트 레벨 커뮤니티(C0)가 TS 대비 97% 적은 토큰으로 비슷한 성능을 낸다.

이 결과가 ASTER에서 하이브리드 구조를 쓰는 실험적 근거가 된다. GraphRAG는 글로벌 패턴 파악에 강하고 벡터 RAG는 로컬 사실과 간결한 답변에 강하다. 두 방법의 강점이 서로 다른 곳에 있다면, 병렬로 둘 다 쓰는 구조가 어느 한쪽만 쓰는 것보다 이론적으로 우위를 갖는다.

---

## Section 6~7: Discussion & Conclusion

한계로는 두 코퍼스에만 테스트했다는 점을 인정한다. 그리고 Future work에 이런 문장이 있다.

> "Hybrid RAG schemes that combine embedding-based matching with just-in-time community report generation before map-reduce"

HybridRAG 논문이 바로 이 방향의 후속 연구다.

---

## ASTER 관점

GraphRAG의 방법론 중 ASTER가 실제로 구현에 쓸 것은 섹션 3.1.2, 즉 엔티티-관계 추출 프롬프트 구조와 Self-reflection 기법이다. 나머지(커뮤니티 탐지, map-reduce)는 배치 처리 구조에서 불필요하다.

| GraphRAG 개념 | ASTER 적용 |
|---|---|
| 엔티티 타입 커스터마이징 (few-shot) | `entity_types = [AspectTerm, OpinionTerm, SentimentPolarity]` |
| 관계에 설명 + 강도 부여 | (aspect, opinion) 엣지에 `sentiment=NEG, count=47` 속성 |
| 커뮤니티 요약 = narrative 형태 | narrative summary injection의 이론적 근거 |
| Map-reduce 글로벌 답변 | 배치 구조라 불필요 |
