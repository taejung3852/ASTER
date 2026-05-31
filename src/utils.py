import json
from langchain_google_genai import ChatGoogleGenerativeAI

# 변수명 앞에 '_'를 붙이면 노출되지 않는다고 한다.
_MODEL = "gemini-3.1-flash-lite"

# JSON 응답이 필요한 노드 (extractor, classifier, critic)
llm_json = ChatGoogleGenerativeAI(
    model=_MODEL,
    temperature=0.0,
    response_mime_type="application/json",
)

# 자연어 응답이 필요한 노드 (synthesizer)
llm_text = ChatGoogleGenerativeAI(
    model=_MODEL,
    temperature=0.3,
)


def _extract_content(response) -> str:
    """response.content가 str이든 list이든 문자열로 추출한다."""
    content = response.content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return content


def parse_json_response(response) -> dict:
    """LLM 응답에서 JSON을 파싱한다."""
    return json.loads(_extract_content(response))


def parse_text_response(response) -> str:
    """LLM 텍스트 응답을 문자열로 반환한다."""
    return _extract_content(response)
