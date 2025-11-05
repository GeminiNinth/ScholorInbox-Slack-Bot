# Scholar Inbox Slack Bot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`scholar-inbox-slack-bot` は、論文推薦サービス「[Scholar Inbox](https://scholar-inbox.com/)」からの推薦論文を自動的に取得し、LLM（OpenAI API）を使って日本語に翻訳・要約してSlackに通知するPythonアプリケーションです。

## 概要

多くの研究者にとって、日々発表される膨大な論文の中から重要なものを見つけ出し、内容を把握するのは大きな負担です。このボットは、Scholar Inboxが提供するパーソナライズされた論文リストを定期的にチェックし、各論文の要点を日本語でまとめてSlackに投稿することで、最新の学術動向を効率的にキャッチアップする手助けをします。

## 主な機能

- **定期実行**: 指定した時間に自動で論文情報をチェックします（例：平日の毎日12時）。
- **論文情報の取得**: [Playwright](https://playwright.dev/python/) を利用してScholar Inboxにアクセスし、タイトル、著者、Abstract、画像などの情報を取得します。
- **複数LLMプロバイダー対応**: OpenAI、Anthropic (Claude)、Google (Gemini) の3つのLLMプロバイダーをサポートします。
- **LLMによる翻訳・要約**: 選択したLLM (GPT-4.1 Mini、GPT-4.1 Nano、Gemini 2.5 Flashなど) を活用し、以下の処理を自動で行います。
  - 論文のAbstractを日本語に翻訳します。
  - 論文の本文（arXivのHTML版）を取得し、指定した観点（「どんなもの？」「先行研究と比べてどこがすごい？」など）で詳細な要約を生成します。
- **Slackへの通知**: [slack-sdk](https://slack.dev/python-slack-sdk/) を用いて、論文1件ごとにスレッドを作成し、整形された情報を投稿します。
  - 親メッセージには論文の基本情報と翻訳済みAbstractを投稿します。
  - スレッド内には、詳細な要約や論文中の図（Teaser Figures）を個別に投稿します。
- **APIコストトラッキング**: LLM APIの使用状況（トークン数、コスト、処理時間）を論文ごと・全体で自動集計し、ログに出力します。
- **柔軟な設定**: `config.yaml` ファイルで、実行スケジュール、要約の観点、Slackへの投稿内容などを自由にカスタマイズできます。
- **安全な認証情報管理**: `.env` ファイルでAPIキーやシークレットURLを安全に管理します。

## システム構成

![システム構成図](system_architecture.png)

## 必要なもの

このボットを実行するには、以下のアカウントと認証情報が必要です。

- **Scholar InboxのシークレットURL**: あなた専用の論文リストページのURL。
- **Slack Bot Token**: Slack APIと連携するためのボットトークン。
- **Slack Channel ID**: 投稿先のチャンネルID（個人のDMに送る場合はご自身のユーザーID）。
- **LLM API Key**: 翻訳と要約に使用するLLMプロバイダーのAPIキー（OpenAI、Anthropic、またはGoogle）。

## セットアップ手順

### 0. uv run 1つでのクイックスタート（推奨）

`uv` がインストール済みであれば、以下のコマンド1つで仮想環境の作成・依存関係の同期・Playwright のブラウザ準備・アプリの起動まで自動で完了します。

```bash
uv run -m src --mode once
```

初回実行時は Playwright の Chromium ブラウザが自動的にダウンロードされるため数分かかることがあります。2回目以降は即座に起動できます。

常駐運用したい場合は `--mode scheduled` を指定してください。

```bash
uv run -m src --mode scheduled
```

その他のオプション（`--date` や `--max-papers` など）はそのまま同じコマンドの後ろに付ければ利用できます。

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-username/scholar-inbox-slack-bot.git
cd scholar-inbox-slack-bot
```

### 2. 仮想環境の作成と依存関係のインストール（手動手順が必要な場合）

コマンド1つでの実行に加えて、手動で仮想環境を管理したい場合は以下の手順で従来どおりセットアップできます。本プロジェクトでは高速なPythonパッケージマネージャーである `uv` を使用します。

```bash
# uvをインストール (pipxを推奨)
pipx install uv

# 仮想環境を作成
uv venv

# 仮想環境を有効化
source .venv/bin/activate

# 依存関係をインストール
uv pip install -r requirements.txt

# Playwright用のブラウザをインストール（uv run コマンドからも自動で実行されます）
uv run playwright install chromium
```

### 3. 設定ファイルの作成

`.env.example` と `config.yaml` を参考に、設定ファイルを作成します。

#### `.env` ファイル

`.env.example` をコピーして `.env` を作成し、あなたの認証情報を記述します。

```bash
cp .env.example .env
```

```dotenv
# .env

# Scholar InboxのシークレットアクセスURL
SCHOLAR_INBOX_SECRET_URL="https://scholar-inbox.com/login/YOUR_SECRET_KEY"

# Slack Bot Token (xoxb- から始まるトークン)
SLACK_BOT_TOKEN="xoxb-YOUR-SLACK-BOT-TOKEN"

# Slackの投稿先チャンネルID
SLACK_CHANNEL_ID="D0123456789"

# LLM APIキー (使用するプロバイダーに応じて設定)
OPENAI_API_KEY="sk-YOUR-OPENAI-API-KEY"
# ANTHROPIC_API_KEY="sk-ant-YOUR-ANTHROPIC-API-KEY"
# GOOGLE_API_KEY="YOUR-GOOGLE-API-KEY"
```

#### `config.yaml` ファイル

`config.yaml` を編集して、ボットの挙動をカスタマイズします。デフォルト設定のままでも動作します。

## 実行方法

### 一度だけ実行する（テスト用）

すぐにボットを実行して動作を確認したい場合は、`--mode once` オプションを使用します。

```bash
uv run -m src --mode once
```

このコマンドだけで仮想環境の構築・依存関係のインストール・Playwright ブラウザのセットアップが自動的に行われます。

`--max-papers` オプションで処理する論文数を制限することもできます。

```bash
# 最初の2件の論文のみ処理する
uv run -m src --mode once --max-papers 2
```

### 日付を指定して実行する

過去の特定日付や日付範囲の論文を取得できます。

```bash
# 特定の日付の論文を取得
uv run -m src --mode once --date "2025-10-31"

# 日付範囲を指定（複数の区切り文字に対応）
uv run -m src --mode once --date "2025-10-31 to 2025-11-02"
uv run -m src --mode once --date "2025-10-31:2025-11-02"
uv run -m src --mode once --date "2025-10-31..2025-11-02"

# 様々な日付フォーマットに対応
uv run -m src --mode once --date "10-31-2025"      # MM-DD-YYYY
uv run -m src --mode once --date "2025/10/31"      # YYYY/MM/DD
uv run -m src --mode once --date "20251031"        # YYYYMMDD
```

**日付指定の注意事項**:
- デフォルトでは30日までの範囲を指定できます。それを超えると警告が表示されます。
- 未来の日付を指定するとエラーになります。
- 1年以上前の日付は警告が表示されますが、実行は可能です。

### スケジュール実行する

設定したスケジュールでボットを常駐させるには、以下のコマンドを実行します。

```bash
uv run -m src --mode scheduled
```

初回実行でPlaywrightのブラウザが未インストールの場合も、自動的にダウンロードが実行されます。

ボットはバックグラウンドで実行され、`config.yaml` で指定された時間にタスクをトリガーします。停止するには `Ctrl+C` を押してください。

### Dockerでワンコマンド実行する（任意）

Docker を使用する場合は、以下の単一コマンドでイメージのビルドから実行までまとめて行えます（POSIXシェル想定）。

```bash
docker run --rm \
  --env-file .env \
  -v "$(pwd)/config.yaml:/app/config.yaml:ro" \
  -v "$(pwd)/data:/app/data" \
  $(docker build -q .) \
  --mode once
```

`--mode scheduled` に差し替えれば常駐モードで起動できます。`config.yaml` や `data/` ディレクトリをホストと共有するため、設定・キャッシュはホスト側のファイルをそのまま利用可能です。

## 設定ファイルの詳細

### `config.yaml`

| キー | 説明 |
| :--- | :--- |
| `language` | 翻訳・要約のターゲット言語 (`ja`, `en` など)。 |
| `llm.provider` | 使用するLLMプロバイダー (`openai`, `anthropic`, `google`)。 |
| `llm.model` | 使用するモデル名（例: `gpt-4.1-mini`, `gpt-4.1-nano`, `gemini-2.5-flash`）。 |
| `llm.temperature` | LLMの温度パラメータ（0.0〜1.0）。 |
| `schedule.check_time` | 論文をチェックする時刻（`HH:MM`形式）。 |
| `schedule.weekdays_only` | `true`にすると月〜金のみ実行します。 |
| `slack.post_elements` | Slackに投稿する項目を `true`/`false` で制御します。 |
| `summary.max_length` | 各要約セクションの最大文字数。 |
| `summary.custom_instructions` | LLMに与える共通の指示。 |
| `summary.sections` | 要約を生成する際の観点（`name`）とプロンプト（`prompt`）のリスト。 |
| `arxiv.prefer_html` | `true`にすると、PDF版よりHTML版の論文を優先して取得します。 |

### `.env`

| キー | 説明 |
| :--- | :--- |
| `SCHOLAR_INBOX_SECRET_URL` | あなたのScholar InboxのシークレットURL。 |
| `SLACK_BOT_TOKEN` | Slackアプリのボットトークン。 |
| `SLACK_CHANNEL_ID` | 通知を送信するSlackチャンネルのID。 |
| `OPENAI_API_KEY` | OpenAIのAPIキー（provider: openai の場合）。 |
| `ANTHROPIC_API_KEY` | AnthropicのAPIキー（provider: anthropic の場合）。 |
| `GOOGLE_API_KEY` | GoogleのAPIキー（provider: google の場合）。 |

## プロジェクト構造

```
scholar-inbox-slack-bot/
├── .env.example          # 環境変数テンプレート
├── .env                  # 環境変数ファイル (Git管理外)
├── config.yaml           # アプリケーション設定ファイル
├── pyproject.toml        # プロジェクト定義ファイル (uv用)
├── README.ja.md          # このファイル
├── requirements.txt      # 依存ライブラリリスト
├── src/
│   ├── main.py           # メイン処理、エントリーポイント
│   ├── scraper.py        # Scholar Inboxのスクレイピング処理
│   ├── slack_client.py   # Slackへの投稿処理
│   ├── llm_client.py     # OpenAI APIとの連携処理
│   ├── scheduler.py      # タスクスケジューリング処理
│   ├── config.py         # 設定ファイルの読み込み処理
│   └── models.py         # Pydanticデータモデル定義
└── data/
    └── cache/            # 一時ファイル（ダウンロードした画像など）の保存場所
```

## LLMプロバイダーの選択

### OpenAI (GPT-4)

```yaml
# config.yaml
llm:
  provider: openai
  model: gpt-4
  temperature: 0.3
```

```env
# .env
OPENAI_API_KEY="sk-your-key"
```

### Anthropic (Claude)

```yaml
# config.yaml
llm:
  provider: anthropic
  model: claude-3-5-sonnet-20241022
  temperature: 0.3
```

```env
# .env
ANTHROPIC_API_KEY="sk-ant-your-key"
```

### Google (Gemini)

```yaml
# config.yaml
llm:
  provider: google
  model: gemini-2.0-flash-exp
  temperature: 0.3
```

```env
# .env
GOOGLE_API_KEY="your-key"
```

## スクレイパーの動作

### タイムアウト設定（検証済み）

Scholar Inboxからの論文取得には以下のタイムアウト設定が使用されます：

- **ページナビゲーション**: 90秒（networkidle待機）
- **メインコンテンツ読み込み**: 20秒
- **Abstractボタン待機**: 30秒
- **React レンダリング**: 8秒
- **スクロール間隔**: 2秒 × 5回
- **Abstract クリック後**: 2秒
- **Show more クリック後**: 3秒

これらの設定は実際のページで検証済みで、安定して動作します。

### リコメンド論文の抽出

Scholar Inboxでは、リコメンド論文（ピンク背景）とヘッダー論文（青背景）が異なるHTML構造を持っています：

- **ヘッダー論文**: タイトルと著者が1つの`<a>`タグに結合（`Title | Authors et al.`形式）
- **リコメンド論文**: タイトルと著者が別々の`<a>`タグ

スクレイパーは同じarXiv IDを持つリンクをグループ化し、タイトルリンクと著者リンクの両方を持つ論文のみを抽出することで、リコメンド論文を正確に識別します。

## テスト

このプロジェクトには包括的なテストスイートが含まれています。

```bash
# 全テストを実行
uv run pytest

# カバレッジレポート付きで実行
uv run pytest --cov=src --cov-report=html

# 特定のテストのみ実行
uv run pytest tests/test_date_utils.py -v
```

**テストカバレッジ**: 51%（主要モジュールは85%以上）

詳細は[TESTING.ja.md](TESTING.ja.md)を参照してください。

## ライセンス

このプロジェクトは [MIT License](LICENSE) の下で公開されています。

## 貢献

バグ報告、機能改善の提案、プルリクエストを歓迎します。Issueを作成するか、フォークしてプルリクエストを送ってください。
