"""Calculate average rating for accepted papers in NeurIPS 2025."""

import json
from pathlib import Path


def calculate_accepted_papers_avg_rating() -> float:
    """採択論文の平均評価を計算する.
    
    Note: all_papers.jsonには採択論文のみが含まれています。
    
    Returns
    -------
        採択論文の平均評価値
    """
    papers_file = Path("storage/papers_data/NeurIPS_2025/all_papers.json")
    
    if not papers_file.exists():
        print(f"Papers file not found: {papers_file}")
        return 0.0
    
    print(f"Loading papers from {papers_file}...")
    papers = json.loads(papers_file.read_text(encoding="utf-8"))
    print(f"Total accepted papers loaded: {len(papers)}")
    print("(Note: all_papers.json contains only accepted papers)")
    
    # すべての論文が採択論文なので、全論文を使用
    accepted_papers = papers
    
    print(f"\nCalculating average rating for {len(accepted_papers)} papers...")
    
    # 採択論文の平均評価を計算
    total_rating = 0.0
    count = 0
    
    for paper in accepted_papers:
        reviews = paper.get("reviews", [])
        if reviews:
            # 各論文のレビュー評価の平均を計算
            paper_ratings = []
            for review in reviews:
                rating_str = review.get("rating", "")
                if rating_str:
                    try:
                        # "5" や "5/10" のような形式に対応
                        rating_value = float(rating_str.split("/")[0].strip())
                        paper_ratings.append(rating_value)
                    except (ValueError, IndexError):
                        continue
            
            if paper_ratings:
                paper_avg = sum(paper_ratings) / len(paper_ratings)
                total_rating += paper_avg
                count += 1
    
    if count == 0:
        print("No ratings found in accepted papers")
        return 0.0
    
    avg_rating = total_rating / count
    
    # 結果を表示
    print("\n" + "=" * 80)
    print("📊 採択論文の評価統計")
    print("=" * 80)
    print(f"✓ 採択論文数: {len(accepted_papers)}")
    print(f"✓ 評価データあり: {count}件")
    print(f"✓ 採択論文の平均評価: {avg_rating:.2f}/10")
    print("=" * 80)
    
    # 評価分布も表示
    rating_distribution = {}
    for paper in papers:
        reviews = paper.get("reviews", [])
        if reviews:
            paper_ratings = []
            for review in reviews:
                rating_str = review.get("rating", "")
                if rating_str:
                    try:
                        rating_value = float(rating_str.split("/")[0].strip())
                        paper_ratings.append(rating_value)
                    except (ValueError, IndexError):
                        continue
            
            if paper_ratings:
                paper_avg = sum(paper_ratings) / len(paper_ratings)
                rating_bucket = int(paper_avg)
                rating_distribution[rating_bucket] = rating_distribution.get(rating_bucket, 0) + 1
    
    print("\n📈 評価分布:")
    for rating in sorted(rating_distribution.keys()):
        count_dist = rating_distribution[rating]
        bar = "█" * (count_dist // 10)
        print(f"  {rating}/10: {count_dist:4d} {bar}")
    
    return avg_rating


def main() -> None:
    """メイン実行関数."""
    avg_rating = calculate_accepted_papers_avg_rating()
    
    print(f"\n💡 推奨設定値:")
    print(f"   min_rating={avg_rating:.2f}  # 採択論文の平均評価")
    print(f"   または")
    print(f"   min_rating={avg_rating - 0.5:.2f}  # 平均より少し低めに設定")
    print(f"\n📝 Note:")
    print(f"   - このデータには採択された論文のみが含まれています")
    print(f"   - 実際の投稿件数はこれより多く、採択率は通常20-30%程度です")


if __name__ == "__main__":
    main()

