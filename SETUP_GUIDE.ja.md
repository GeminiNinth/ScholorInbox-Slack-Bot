# Scholar Inbox Slack Bot セットアップガイド

このガイドでは、Scholar Inbox Slack Botを初めて使う方向けに、詳細なセットアップ手順を説明します。

## 目次

1. [事前準備](#事前準備)
2. [Scholar Inboxのシークレット URLの取得](#scholar-inboxのシークレット-urlの取得)
3. [Slack Botの作成とトークン取得](#slack-botの作成とトークン取得)
4. [OpenAI APIキーの取得](#openai-apiキーの取得)
5. [ボットのインストールと設定](#ボットのインストールと設定)
6. [動作確認](#動作確認)
7. [トラブルシューティング](#トラブルシューティング)

---

## 事前準備

以下のものが必要です。

- **Python 3.11以上**がインストールされていること
- **Git**がインストールされていること
- **インターネット接続**

### Pythonのバージョン確認

```bash
python3 --version
```

Python 3.11以上が表示されればOKです。

---

## Scholar Inboxのシークレット URLの取得

1. [Scholar Inbox](https://scholar-inbox.com/)にアクセスし、アカウントを作成またはログインします。
2. ダッシュボードまたは設定ページから、あなた専用の**シークレットアクセスURL**を見つけます。
   - URLは通常 `https://scholar-inbox.com/login/YOUR_SECRET_KEY` の形式です。
3. このURLをコピーして、後で`.env`ファイルに貼り付けます。

---

## Slack Botの作成とトークン取得

### 1. Slack Appの作成

1. [Slack API](https://api.slack.com/apps)にアクセスし、「**Create New App**」をクリックします。
2. 「**From scratch**」を選択します。
3. **App Name**に適当な名前（例: `Scholar Inbox Bot`）を入力し、**Workspace**を選択して「**Create App**」をクリックします。

### 2. Bot Tokenの取得

1. 左メニューから「**OAuth & Permissions**」を選択します。
2. 「**Scopes**」セクションで「**Bot Token Scopes**」に以下の権限を追加します。
   - `chat:write` (メッセージを投稿する)
   - `files:write` (ファイルをアップロードする)
   - `channels:read` (チャンネル情報を読む)
   - `groups:read` (プライベートチャンネル情報を読む)
   - `im:write` (ダイレクトメッセージを送る)
3. ページ上部の「**Install to Workspace**」ボタンをクリックし、Slackワークスペースにアプリをインストールします。
4. インストール後、「**Bot User OAuth Token**」が表示されます。これは `xoxb-` で始まるトークンです。
5. このトークンをコピーして、後で`.env`ファイルに貼り付けます。

### 3. Slack Channel IDの取得

ボットが投稿するチャンネルのIDを取得します。

- **個人DMに送る場合**: あなた自身のユーザーIDが必要です。
  1. Slackのデスクトップアプリまたはブラウザ版を開きます。
  2. 自分のプロフィールをクリックし、「**プロフィールを表示**」を選択します。
  3. 「**その他**」→「**メンバーIDをコピー**」を選択します。
  4. このIDは `U0123456789` のような形式です。

- **特定のチャンネルに送る場合**:
  1. チャンネルを開き、チャンネル名をクリックします。
  2. 下部に表示される「**チャンネルID**」をコピーします。
  3. このIDは `C0123456789` のような形式です。

---

## OpenAI APIキーの取得

1. [OpenAI Platform](https://platform.openai.com/)にアクセスし、アカウントを作成またはログインします。
2. 右上のアカウントメニューから「**API keys**」を選択します。
3. 「**Create new secret key**」をクリックし、新しいAPIキーを生成します。
4. 生成されたキーをコピーします（**一度しか表示されません**）。
5. このキーを後で`.env`ファイルに貼り付けます。

**注意**: OpenAI APIは有料です。使用量に応じて課金されるため、[料金ページ](https://openai.com/pricing)を確認してください。

---

## ボットのインストールと設定

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-username/scholar-inbox-slack-bot.git
cd scholar-inbox-slack-bot
```

### 2. uvのインストール

`uv`は高速なPythonパッケージマネージャーです。

```bash
# pipxを使用してuvをインストール (推奨)
pipx install uv

# または、pipを使用
pip install uv
```

### 3. 仮想環境の作成と依存関係のインストール

```bash
# 仮想環境を作成
uv venv

# 仮想環境を有効化
source .venv/bin/activate  # Linuxまたは macOS
# または
.venv\Scripts\activate  # Windows

# 依存関係をインストール
uv pip install -r requirements.txt

# Playwrightのブラウザをインストール
uv run playwright install chromium
```

### 4. 環境変数ファイルの作成

```bash
cp .env.example .env
```

`.env`ファイルを開き、取得した情報を入力します。

```dotenv
# Scholar InboxのシークレットアクセスURL
SCHOLAR_INBOX_SECRET_URL="https://scholar-inbox.com/login/YOUR_SECRET_KEY"

# Slack Bot Token
SLACK_BOT_TOKEN="xoxb-YOUR-SLACK-BOT-TOKEN"

# Slackの投稿先チャンネルID
SLACK_CHANNEL_ID="U0123456789"

# OpenAI APIキー
OPENAI_API_KEY="sk-YOUR-OPENAI-API-KEY"
```

### 5. 設定ファイルのカスタマイズ（オプション）

`config.yaml`を編集して、実行時間や要約の観点などをカスタマイズできます。

```yaml
# 実行時刻を変更する例
schedule:
  check_time: "09:00"  # 毎朝9時に実行
  weekdays_only: true
```

---

## 動作確認

### テスト実行

まず、1件の論文だけを処理してみます。

```bash
uv run python src/main.py --mode once --max-papers 1
```

実行すると、以下のような処理が行われます。

1. Scholar Inboxにアクセスして論文情報を取得
2. OpenAI APIで翻訳と要約を生成
3. Slackに投稿

ログが表示され、最後に「Successfully processed paper 1」と表示されれば成功です。

### Slackで確認

指定したチャンネルまたはDMに、論文情報が投稿されているか確認してください。

---

## スケジュール実行

テストが成功したら、スケジュール実行モードで起動します。

```bash
uv run python src/main.py --mode scheduled
```

ボットはバックグラウンドで動作し、`config.yaml`で指定した時刻に自動で論文をチェックします。

停止するには `Ctrl+C` を押してください。

---

## トラブルシューティング

### エラー: "Missing required environment variables"

`.env`ファイルが正しく設定されていません。以下を確認してください。

- `.env`ファイルがプロジェクトのルートディレクトリに存在するか
- 各変数が正しく記述されているか（引用符で囲む）
- ファイル名が`.env`であるか（`.env.example`ではない）

### エラー: "Slack API error: invalid_auth"

Slack Bot Tokenが無効です。以下を確認してください。

- トークンが `xoxb-` で始まっているか
- トークンをコピーする際にスペースが入っていないか
- Slack Appがワークスペースにインストールされているか

### エラー: "OpenAI API error: Incorrect API key"

OpenAI APIキーが無効です。以下を確認してください。

- APIキーが `sk-` で始まっているか
- APIキーが正しくコピーされているか
- OpenAIアカウントに支払い方法が登録されているか

### 論文が取得できない

Scholar InboxのURLが間違っているか、ページの構造が変わった可能性があります。

- URLが正しいか確認してください
- ブラウザで直接URLにアクセスして、論文リストが表示されるか確認してください

### その他の問題

ログファイル `scholar_inbox_bot.log` を確認して、詳細なエラーメッセージを確認してください。

```bash
tail -f scholar_inbox_bot.log
```

---

## サポート

問題が解決しない場合は、GitHubのIssueで報告してください。
