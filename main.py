import os
import json

# LangSmith 트레이싱 설정 — .env 또는 환경변수로 주입
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "aster")

from src.graph import app


def run_pipeline(reviews: list[str], domain: str = "telecom") -> dict:
    initial_state = {
        "reviews": reviews,
        "domain": domain,
    }
    result = app.invoke(initial_state)
    return result


if __name__ == "__main__":
    sample_reviews = [
        "요금이 너무 비싸서 해지를 고려하고 있어요. 데이터 속도는 그럭저럭 괜찮은데.",
        "고객센터에 전화했는데 30분 넘게 기다렸어요. 상담원은 친절했지만 시간이 너무 걸렸습니다.",
        "5G 속도가 생각보다 훨씬 빠르네요! 요금제 가격 대비 만족스럽습니다.",
    ]

    result = run_pipeline(sample_reviews, domain="telecom")

    print("=== ASTE 결과 ===")
    for triple in result["aste_results"]:
        print(
            f"  [{triple['sentiment']}] {triple['aspect']} / {triple['opinion']}"
            f" (신뢰도: {triple['confidence']:.2f})"
        )
        print(f"    근거: {triple['evidence']}")

    print("\n=== 액션 권고 ===")
    print(result["action_recommendations"])

    print("\n=== 집계 통계 ===")
    for aspect, stats in result["aggregated_stats"].items():
        print(f"  {aspect}: NEG {stats['neg_ratio']*100:.1f}%")
