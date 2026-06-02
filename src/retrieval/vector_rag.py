"""
Vector RAG: Qdrant 기반 유사 리뷰 검색.
초기 개발: :memory: 모드. 운영 전환 시 host/port 설정으로 교체.
"""
from typing import List, Optional
import os

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from langchain_google_genai import GoogleGenerativeAIEmbeddings

_client: Optional[QdrantClient] = None
_embedder: Optional[GoogleGenerativeAIEmbeddings] = None
_COLLECTION = "absa_reviews"
_VECTOR_DIM = 768


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        qdrant_url = os.getenv("QDRANT_URL")
        if qdrant_url:
            _client = QdrantClient(url=qdrant_url)
        else:
            _client = QdrantClient(":memory:")
        _client.recreate_collection(
            collection_name=_COLLECTION,
            vectors_config=VectorParams(size=_VECTOR_DIM, distance=Distance.COSINE),
        )
    return _client


def _get_embedder() -> GoogleGenerativeAIEmbeddings:
    global _embedder
    if _embedder is None:
        _embedder = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    return _embedder


def upsert(reviews: List[str], domain: str) -> None:
    """리뷰를 벡터 DB에 삽입한다."""
    client = _get_client()
    embedder = _get_embedder()
    vectors = embedder.embed_documents(reviews)
    points = [
        PointStruct(
            id=i,
            vector=v,
            payload={"text": r, "domain": domain},
        )
        for i, (r, v) in enumerate(zip(reviews, vectors))
    ]
    client.upsert(collection_name=_COLLECTION, points=points)


def search(reviews: List[str], domain: str, top_k: int = 3) -> str:
    """쿼리 리뷰와 유사한 리뷰를 검색해 컨텍스트 문자열로 반환한다."""
    client = _get_client()
    embedder = _get_embedder()

    query_text = " ".join(reviews[:3])  # 배치 대표 쿼리
    query_vector = embedder.embed_query(query_text)

    results = client.search(
        collection_name=_COLLECTION,
        query_vector=query_vector,
        limit=top_k,
        query_filter=Filter(
            must=[FieldCondition(key="domain", match=MatchValue(value=domain))]
        ),
    )

    if not results:
        return ""

    lines = [f"- {r.payload['text']} (유사도 {r.score:.2f})" for r in results]
    return "\n".join(lines)
