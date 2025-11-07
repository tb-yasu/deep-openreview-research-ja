"""Constants for paper review workflow."""

# ランキング関連
DEFAULT_TOP_N_PAPERS = 20  # デフォルトのトップN論文数
MAX_DISPLAY_PAPERS = 20    # 表示する最大論文数

# LLM評価関連
DEFAULT_LLM_MAX_TOKENS = 1000      # LLM評価のデフォルト最大トークン数
DEFAULT_LLM_TEMPERATURE = 0.0      # LLM評価のデフォルト温度
DEFAULT_LLM_TIMEOUT = 60           # LLM評価のデフォルトタイムアウト（秒）
PRELIMINARY_LLM_MAX_TOKENS = 50    # 簡易LLM評価の最大トークン数

# テキスト処理関連
ABSTRACT_SHORT_LENGTH = 300        # アブストラクト短縮の文字数
MAX_KEYWORDS_DISPLAY = 8           # 表示する最大キーワード数
MAX_AUTHORS_DISPLAY = 5            # 表示する最大著者数
MAX_RATIONALE_LENGTH = 500         # 評価理由の最大文字数

# 同義語生成関連
SYNONYMS_LLM_MAX_TOKENS = 200      # 同義語生成の最大トークン数
SYNONYMS_COUNT_MIN = 3             # 最小同義語数
SYNONYMS_COUNT_MAX = 5             # 最大同義語数

# キャッシュ関連
DEFAULT_CACHE_TTL_HOURS = 24       # キャッシュのデフォルトTTL（時間）
CACHE_DIR_NAME = "storage/cache"   # キャッシュディレクトリ名

# スコアリング関連
MIN_SCORE = 0.0                    # 最小スコア値
MAX_SCORE = 1.0                    # 最大スコア値
NEURIPS_RATING_SCALE = 10.0        # NeurIPSのレーティングスケール

# 関連性スコア計算の重み
RELEVANCE_KEYWORD_WEIGHT = 0.70    # 論文keywordマッチの重み
RELEVANCE_TEXT_WEIGHT = 0.20       # タイトル/アブストラクトマッチの重み
RELEVANCE_COVERAGE_WEIGHT = 0.10   # カバレッジの重み

