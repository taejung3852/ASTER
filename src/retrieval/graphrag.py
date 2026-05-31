"""
GraphRAG MVP: networkx 기반 aspect 공동출현 그래프.
Phase 2에서 GRAGLLM 논문 분석 후 Microsoft GraphRAG 또는 논문 방식으로 교체.
"""
from typing import List
import networkx as nx


_graphs: dict[str, nx.Graph] = {}  # domain → 공동출현 그래프 (인메모리)


def build_graph(aspects_per_review: List[List[str]], domain: str) -> None:
    """리뷰 배치로 공동출현 그래프를 구축하거나 업데이트한다."""
    if domain not in _graphs:
        _graphs[domain] = nx.Graph()

    g = _graphs[domain]
    for aspect_list in aspects_per_review:
        for i, a in enumerate(aspect_list):
            g.add_node(a)
            for b in aspect_list[i + 1:]:
                if g.has_edge(a, b):
                    g[a][b]["weight"] += 1
                else:
                    g.add_edge(a, b, weight=1)


def search(reviews: List[str], domain: str, top_k: int = 5) -> str:
    """
    리뷰 텍스트에서 키워드를 추출하고 그래프에서 관련 aspect 패턴을 반환한다.
    그래프가 비어있으면 빈 컨텍스트 반환.
    """
    if domain not in _graphs or len(_graphs[domain].nodes) == 0:
        return ""

    g = _graphs[domain]
    all_text = " ".join(reviews)
    matched_nodes = [n for n in g.nodes if n in all_text]

    if not matched_nodes:
        return ""

    context_lines = []
    for node in matched_nodes[:top_k]:
        neighbors = sorted(
            g[node].items(), key=lambda x: -x[1]["weight"]
        )[:3]
        if neighbors:
            neighbor_str = ", ".join(f"{n}(공동출현 {d['weight']}회)" for n, d in neighbors)
            context_lines.append(f"- '{node}'과 자주 함께 언급되는 aspect: {neighbor_str}")

    return "\n".join(context_lines) if context_lines else ""
