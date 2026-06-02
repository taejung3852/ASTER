# HybridRAG

> arXiv:2408.04948 | "HybridRAG: Integrating Knowledge Graphs and Vector Retrieval Augmented Generation for Efficient Information Extraction"
> Bhaskarjit Sarmah et al., BlackRock / NVIDIA (2024)

---

## Abstract

금융 문서는 전문 용어와 복잡한 포맷 때문에 기존 VectorRAG로는 정보 추출이 잘 안 된다. 이 논문은 VectorRAG와 GraphRAG를 결합한 HybridRAG를 제안하고, 인도 Nifty-50 기업의 어닝콜 전사 데이터로 실험해 두 단일 방법 각각보다 낫다는 걸 보인다. 특이한 점은 검색 단계와 생성 단계를 분리해 평가했다는 것이다. 앞선 GraphRAG 논문이 최종 답변의 품질만 비교했다면, 이 논문은 "검색이 잘 됐는가"와 "생성이 잘 됐는가"를 따로 측정한다.

이 논문이 ASTER에 주는 것은 성능 수치가 아니라 구조적 통찰이다. 두 방법의 실패 지점이 다르다는 분석이 하이브리드 구조를 쓰는 논리적 근거가 된다.

---

## Section 1: Introduction

논문은 VectorRAG와 GraphRAG 각각의 약점에서 시작한다. VectorRAG는 문단 단위 청킹이 텍스트 길이가 균일하다고 가정하기 때문에 금융 문서의 계층 구조를 무시하고, 방대한 코퍼스에서 컨텍스트 품질이 들쑥날쑥하다. GraphRAG는 추출형 질문에는 강하지만, 질문에 명시적 엔티티가 없거나 원문에 직접 표현되지 않은 추상적 답변이 필요할 때 성능이 떨어진다.

두 방법의 약점이 겹치지 않는다는 것이 이 논문의 핵심 관찰이다. VectorRAG가 실패하는 지점에서 GraphRAG가 강하고, GraphRAG가 실패하는 지점에서 VectorRAG가 강하다. 그러므로 둘을 합치면 서로의 실패를 메울 수 있다. 논문은 VectorRAG와 GraphRAG를 명시적으로 하이브리드한 최초의 연구라고 주장한다.

---

## Section 2: Methodology

### VectorRAG

문서를 청크로 분할하고 임베딩해 벡터 DB에 저장한다. 쿼리가 오면 유사도 검색으로 top-k 청크를 꺼내 LLM에 주입한다. 이 논문에서는 회사명·분기·연도 같은 메타데이터를 명시적으로 추가해 성능을 높였다.

### Knowledge Graph 구축

KG 구축은 세 단계 중 두 단계만 쓴다. Knowledge Extraction에서 엔티티 인식·관계 추출·상호참조 해소를 하고, Knowledge Improvement에서 중복 엔티티 병합과 출처 간 충돌 해소를 한다. Knowledge Adaptation은 쓰지 않고 정적 그래프로 취급한다.

주목할 구조가 Two-tiered LLM chain이다. 원문 청크를 바로 트리플 추출에 넣지 않고, 1단계에서 LLM으로 청크의 추상 표현을 먼저 만든다. 노이즈를 제거하고 핵심 정보만 남긴 뒤, 2단계에서 엔티티·관계를 추출하는 방식이다. LightRAG의 -Origin 실험이 발견한 것과 같은 철학이다. 원문에는 노이즈가 많으니 LLM으로 한 번 정제한 뒤 쓰자는 것이다. 서로 독립적인 두 논문이 같은 방향을 가리킨다는 건 그 설계 판단의 근거가 되어준다.

### HybridRAG

구조는 단순하다. VectorRAG로 컨텍스트 A를 검색하고, GraphRAG로 컨텍스트 B를 검색한 뒤, A와 B를 순서대로 이어 붙여 LLM에 주입한다. 정교한 융합 알고리즘이 아니라 concatenate다. VectorRAG 컨텍스트를 먼저, GraphRAG 컨텍스트를 나중에 붙이는데, 뒤에 오는 컨텍스트일수록 context precision이 낮아지는 경향이 있다고 논문이 솔직히 인정한다.

ASTER가 이미 vector_rag와 graphrag 결과를 합쳐 LLM에 주입하는 구조로 설계되어 있다는 점에서, ASTER의 기존 구조가 곧 HybridRAG다.

---

## Section 2.4: 평가 지표

기존 GraphRAG 논문이 최종 답변의 품질(comprehensiveness, diversity 등)만 비교한 것과 달리, 이 논문은 RAGAS 프레임워크로 검색과 생성을 분리해 측정한다.

| 지표 | 대상 | 의미 |
|---|---|---|
| Faithfulness (F) | 생성 | 답변이 주어진 컨텍스트에서 추론 가능한 정도. 답변을 진술 단위로 분해해 LLM이 각각을 검증. `F = 지지된 진술 / 전체 진술` |
| Answer Relevance (AR) | 생성 | 답변이 질문에 부합하는 정도. 답변으로 역질문 n개 생성 → 원질문과 코사인 유사도 평균 |
| Context Precision (CP) | 검색 | 검색된 청크가 정답과 관련된 비율 |
| Context Recall (CR) | 검색 | 정답의 각 문장이 검색된 컨텍스트로 추적 가능한 비율 |

---

## Section 3~4: 데이터 & 구현

Nifty-50(인도 대형주 50개) 기업의 어닝콜 전사 50건을 사용했다. 평균 27페이지, 60,000 토큰 분량이고, 무작위 추출한 400개 Q&A 쌍을 정답지로 썼다. 공개된 금융 벤치마크들(FinQA, FinanceBench 등)은 KG 컨텍스트를 제공하지 않아 세 방법 비교에 쓸 수 없어서 자체 데이터셋을 만들었다.

구현은 VectorRAG에 Pinecone + text-embedding-ada-002 + GPT-3.5-turbo, GraphRAG에 Networkx + GraphQAChain을 썼다. KG는 트리플 13,950개, 노드 11,405개, 엣지 13,883개로 구성됐고, DFS depth=1로 엔티티 주변을 탐색했다.

---

## Section 5: Results

| 지표 | VectorRAG | GraphRAG | HybridRAG |
|---|---|---|---|
| Faithfulness (F) | 0.94 | 0.96 | 0.96 |
| Answer Relevance (AR) | 0.91 | 0.89 | **0.96** |
| Context Precision (CP) | 0.84 | **0.96** | 0.79 |
| Context Recall (CR) | 1.0 | 0.85 | 1.0 |

HybridRAG는 AR에서 단독 1위, F와 CR에서 공동 최고다. 단, CP는 꼴찌다. 두 컨텍스트를 합치면 ground truth와 관련 없는 내용도 섞여 들어가기 때문이다. 논문도 이 trade-off를 인정하면서, 나머지 지표에서의 우위로 정당화한다.

작동 원리는 논문이 직접 설명한다. GraphRAG는 extractive 질문(정답이 원문에 명시된 경우)에 강하고, VectorRAG는 abstractive 질문(정답이 원문에 명시되지 않은 경우)에 강하다. HybridRAG는 VectorRAG가 extractive 질문에서 실패하면 GraphRAG가 fallback으로 채우고, GraphRAG가 abstractive 질문에서 실패하면 VectorRAG가 채운다. 두 방법이 서로의 실패를 자동으로 메우는 구조다.

이 결과를 ASTER의 근거로 쓸 때 주의할 점이 있다. 수치 차이가 0.0X 단위로 작고 유의성 검정(p-value, 신뢰구간)이 없다. n=400, 단일 도메인(금융), 단일 LLM(GPT-3.5) 실험이라 일반화 근거도 약하다. Microsoft GraphRAG의 72~83% 페어 승률과는 설득력 무게가 다르다. 따라서 "HybridRAG가 성능이 우수하다"는 정량 근거로 인용하면 방어가 어렵고, "두 방법의 실패 지점이 달라 상보적이다"는 정성적 통찰로 인용하는 게 맞다.

---

## ASTER 관점

이 논문에서 가져오는 것은 구조적 정당성이다. ASTER의 병렬 검색 구조(vector_rag + graphrag → 합쳐서 주입)가 HybridRAG 패턴과 정확히 일치하고, 이 논문이 그 구조의 이론적·실증적 배경을 제공한다. Microsoft GraphRAG 논문이 Future work로 hybrid RAG를 제시했고, 이 논문이 그것을 실제로 구현하고 검증한 후속 연구라는 점에서 두 논문이 한 묶음의 서사를 이룬다.

쓰지 않는 것은 금융 도메인 특화 구현 세부 사항들이다. ASTER는 Qdrant + networkx로 직접 구성하고, DFS depth-1 탐색도 쓰지 않는다.

HybridRAG가 CP에서 꼴찌인 문제, 즉 컨텍스트를 합치면 노이즈가 섞이는 문제는 ASTER에서도 동일하게 발생할 수 있다. raw triple 대신 narrative summary로 정제해 주입하는 설계가 이 약점을 부분적으로 완화한다.
