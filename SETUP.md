# セットアップガイド

このガイドでは、Paper Review Agentの初期セットアップ手順を説明します。

## 前提条件

- Python 3.12以上
- OpenAI APIキー
- インターネット接続（論文データ取得時のみ）

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/yourusername/paper-review-agent.git
cd paper-review-agent
```

### 2. 仮想環境の作成

```bash
# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

インストールされる主なパッケージ：
- `langchain` - LLMアプリケーションフレームワーク
- `langgraph` - ステートフルなマルチアクターアプリケーション用フレームワーク
- `langchain-openai` - OpenAI統合
- `openreview-py` - OpenReview API クライアント
- `pydantic` - データ検証
- `loguru` - ログ出力

### 4. 環境変数の設定

OpenAI APIキーを環境変数として設定します：

```bash
# macOS/Linux:
export OPENAI_API_KEY="your-api-key-here"

# Windows (コマンドプロンプト):
set OPENAI_API_KEY=your-api-key-here

# Windows (PowerShell):
$env:OPENAI_API_KEY="your-api-key-here"
```

永続的に設定する場合：

**macOS/Linux (bash):**
```bash
echo 'export OPENAI_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

**macOS/Linux (zsh):**
```bash
echo 'export OPENAI_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

**Windows:**
システム環境変数として設定してください。

### 5. 動作確認

セットアップが正しく完了したか確認します：

```bash
# Pythonのバージョン確認
python --version
# 出力: Python 3.12.x 以上

# 依存パッケージの確認
pip list | grep langchain
# 出力: langchain, langgraph, langchain-openai など

# 環境変数の確認
echo $OPENAI_API_KEY  # macOS/Linux
echo %OPENAI_API_KEY%  # Windows
# 出力: your-api-key-here
```

### 6. 論文データの取得

最初に一度だけ、対象学会の論文データを取得します：

```bash
python fetch_all_papers.py --venue NeurIPS --year 2025
```

**注意事項:**
- 初回実行時は60-90分程度かかります
- OpenReview APIのレート制限（60リクエスト/分）に準拠しています
- 進捗は自動保存されるため、中断しても再開できます
- 一度取得すれば、以降はローカルキャッシュを使用します

### 7. テスト実行

クイックスタートスクリプトでテスト実行します：

```bash
./quickstart.sh
```

または、直接実行：

```bash
python run_paper_review.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "グラフ生成に興味があります" \
  --top-k 10
```

## トラブルシューティング

### Q: `ModuleNotFoundError` が発生する

**A:** 仮想環境が有効化されていることを確認してください：

```bash
# 仮想環境を有効化
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# 依存パッケージを再インストール
pip install -r requirements.txt
```

### Q: `OPENAI_API_KEY not found` エラーが出る

**A:** 環境変数が正しく設定されているか確認してください：

```bash
# 確認
echo $OPENAI_API_KEY  # macOS/Linux

# 設定
export OPENAI_API_KEY="your-api-key-here"
```

### Q: OpenReview APIでエラーが発生する

**A:** 以下を確認してください：
- インターネット接続が正常か
- OpenReviewのサービスが稼働しているか（https://openreview.net/）
- レート制限に達していないか（60リクエスト/分）

### Q: 論文データ取得が途中で止まる

**A:** 進捗は自動保存されているため、再度実行すれば続きから再開します：

```bash
# 同じコマンドを再実行
python fetch_all_papers.py --venue NeurIPS --year 2025
```

### Q: メモリ不足エラーが発生する

**A:** `--top-k` の値を小さくしてください：

```bash
python run_paper_review.py \
  --venue NeurIPS \
  --year 2025 \
  --research-description "あなたの研究興味" \
  --top-k 30  # デフォルトの100から減らす
```

## 次のステップ

セットアップが完了したら、以下のドキュメントを参照してください：

- [README.md](README.md) - プロジェクト概要
- [USAGE.md](USAGE.md) - 詳細な使用方法
- [examples.sh](examples.sh) - 使用例スクリプト

## サポート

問題が解決しない場合は、以下の方法でサポートを受けてください：

- **GitHub Issues**: https://github.com/yourusername/paper-review-agent/issues
- **Email**: your-email@example.com

---

**Happy Coding! 🚀**

