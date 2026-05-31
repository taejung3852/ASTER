import json
from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable

from src.state import ABSAState, Aspect, DOMAIN_TAXONOMY
from src.utils import llm_json as _llm
from src.retrieval.graphrag import search as graphrag_search
from src.retrieval.vector_rag import search as vector_search

_SYSTEM = """\
# Role
당신은 고객 리뷰 분석 전문가입니다.
주어진 도메인의 Taxonomy 기준으로 리뷰에서 aspect를 추출합니다.

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
"""


@traceable(name="aspect_extractor")
def aspect_extractor(state: ABSAState) -> dict:
    reviews = state["reviews"]
    domain = state["domain"]
    taxonomy = DOMAIN_TAXONOMY[domain]

    graph_context: Optional[str] = None
    vector_context: Optional[str] = None

    try:
        graph_context = graphrag_search(reviews, domain)
    except Exception:
        pass

    try:
        vector_context = vector_search(reviews, domain)
    except Exception:
        pass

    reviews_str = "\n".join(f"- {r}" for r in reviews)
    human = f"""\
## 분석 도메인
{domain}

## 도메인 Taxonomy
{", ".join(taxonomy)}

## 관련 리뷰 패턴 (GraphRAG)
{graph_context or "없음"}

## 유사 리뷰 예시 (Vector RAG)
{vector_context or "없음"}

## 분석할 리뷰
{reviews_str}
"""

    response = _llm.invoke([SystemMessage(_SYSTEM), HumanMessage(human)])
    parsed = json.loads(response.content)
    aspects: list[Aspect] = parsed.get("aspects", [])

    if not aspects:
        raise ValueError("aspect 추출 결과가 없습니다. 리뷰를 확인하세요.")

    return {
        "aspects": aspects,
        "graph_context": graph_context,
        "vector_context": vector_context,
    }
