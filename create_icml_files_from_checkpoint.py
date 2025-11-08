"""現在のICMLチェックポイントから完全なファイルを作成"""

import json
from pathlib import Path
from datetime import datetime

# ICMLディレクトリ
data_dir = Path("storage/papers_data/ICML_2025")

# 最新のチェックポイントファイルを探す
temp_files = sorted(data_dir.glob("all_papers_temp_*.json"))

if not temp_files:
    print("❌ チェックポイントファイルが見つかりません")
    exit(1)

latest_temp_file = temp_files[-1]
print(f"📖 最新のチェックポイント: {latest_temp_file.name}")

# チェックポイントファイルを読み込み
papers = json.loads(latest_temp_file.read_text(encoding="utf-8"))
print(f"✓ {len(papers)} 件の論文を読み込みました")

# all_papers.json として保存
papers_file = data_dir / "all_papers.json"
papers_file.write_text(
    json.dumps(papers, ensure_ascii=False, indent=2),
    encoding="utf-8"
)
print(f"✓ {papers_file.name} を作成しました")

# 統計情報を計算
papers_with_reviews = sum(1 for p in papers if p.get("reviews"))
papers_with_rating = sum(1 for p in papers if p.get("rating_avg") is not None)

if papers_with_rating > 0:
    avg_rating = sum(p["rating_avg"] for p in papers if p.get("rating_avg") is not None) / papers_with_rating
else:
    avg_rating = 0.0

print(f"\n📊 統計情報:")
print(f"  - 総論文数: {len(papers)}")
print(f"  - レビューあり: {papers_with_reviews} ({papers_with_reviews/len(papers)*100:.1f}%)")
print(f"  - 平均rating: {avg_rating:.2f}")

# metadata.json を作成
metadata = {
    "venue": "ICML",
    "year": 2025,
    "total_papers": len(papers),
    "papers_with_reviews": papers_with_reviews,
    "average_rating": round(avg_rating, 2),
    "fetch_date": datetime.now().isoformat(),
    "file_size_mb": papers_file.stat().st_size / 1024 / 1024,
    "includes_review_data": True,
    "status": "partial",  # 部分ダウンロード
    "note": f"Created from checkpoint {latest_temp_file.name}",
}

metadata_file = data_dir / "metadata.json"
metadata_file.write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2),
    encoding="utf-8"
)
print(f"✓ {metadata_file.name} を作成しました")

print(f"\n✅ 完了！以下のファイルが作成されました:")
print(f"  - {papers_file}")
print(f"  - {metadata_file}")
print(f"\n🚀 これで run_deep_research.py を使用できます：")
print(f"   python run_deep_research.py --venue ICML --year 2025 --research-description '状態空間モデル' --top-k 10")

