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
