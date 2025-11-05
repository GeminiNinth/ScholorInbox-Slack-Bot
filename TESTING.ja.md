# テストガイド

このドキュメントでは、Scholar Inbox Slack Botのテストスイートについて説明します。

## 目次

- [テスト環境のセットアップ](#テスト環境のセットアップ)
- [テストの実行](#テストの実行)
- [テスト構成](#テスト構成)
- [テストカバレッジ](#テストカバレッジ)
- [新しいテストの追加](#新しいテストの追加)

## テスト環境のセットアップ

### 必要な依存関係のインストール

```bash
# プロジェクトディレクトリに移動
cd scholar-inbox-slack-bot

# テスト用の依存関係をインストール
uv add --dev pytest pytest-cov pytest-mock
```

### テスト用の環境変数

テストは自動的にモックされた環境変数を使用するため、実際の`.env`ファイルは不要です。

## テストの実行

### 全テストの実行

```bash
# 全テストを実行
uv run pytest

# 詳細な出力で実行
uv run pytest -v

# 失敗したテストで停止
uv run pytest -x
```

### 特定のテストファイルの実行

```bash
# 日付ユーティリティのテストのみ
uv run pytest tests/test_date_utils.py -v

# 設定管理のテストのみ
uv run pytest tests/test_config.py -v

# LLMクライアントのテストのみ
uv run pytest tests/test_llm_client.py -v
```

### マーカーによるフィルタリング

```bash
# 単体テストのみ実行
uv run pytest -m unit

# 統合テストのみ実行
uv run pytest -m integration

# 遅いテストを除外
uv run pytest -m "not slow"
```

### カバレッジレポートの生成

```bash
# カバレッジ付きでテストを実行
uv run pytest --cov=src --cov-report=term-missing

# HTMLレポートを生成
uv run pytest --cov=src --cov-report=html

# HTMLレポートを開く
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## テスト構成

### テストファイル一覧

| テストファイル | 対象モジュール | テスト数 | 説明 |
|:--------------|:-------------|:--------|:-----|
| `test_date_utils.py` | `date_utils.py` | 19 | 日付解析、日付範囲、URL生成のテスト |
| `test_config.py` | `config.py` | 6 | 設定ファイル読み込み、環境変数のテスト |
| `test_models.py` | `models.py` | 9 | Pydanticデータモデルのテスト |
| `test_scheduler.py` | `scheduler.py` | 7 | スケジューラーのテスト |
| `test_llm_client.py` | `llm_client.py` | 10 | LLM翻訳・要約のテスト |
| `test_slack_client.py` | `slack_client.py` | 10 | Slack投稿のテスト |
| `test_integration.py` | `main.py` | 8 | 統合テスト |

### テストの種類

#### 1. 単体テスト（Unit Tests）

各モジュールの個別機能をテストします。外部依存はモックされます。

**例**: `test_date_utils.py`

```python
def test_parse_date_formats():
    """様々な日付フォーマットの解析をテスト"""
    assert DateParser.parse_date("2025-10-31") == datetime(2025, 10, 31)
    assert DateParser.parse_date("10-31-2025") == datetime(2025, 10, 31)
    assert DateParser.parse_date("2025/10/31") == datetime(2025, 10, 31)
```

#### 2. 統合テスト（Integration Tests）

複数のモジュールが連携して動作することをテストします。

**例**: `test_integration.py`

```python
@pytest.mark.integration
def test_workflow_with_papers():
    """論文取得から投稿までの完全なワークフローをテスト"""
    bot = ScholarInboxBot()
    bot.check_and_post_papers(max_papers=2)
    # 各コンポーネントが正しく呼び出されたことを確認
```

#### 3. 境界条件テスト

エッジケースや異常系をテストします。

**例**: `test_date_utils.py`

```python
def test_validate_date_range_too_large():
    """30日を超える日付範囲のバリデーションをテスト"""
    start = datetime(2025, 1, 1)
    end = datetime(2025, 2, 15)  # 46日
    dr = DateRange(start, end)
    
    is_valid, warning = DateParser.validate_date_range(dr, max_days=30)
    assert is_valid is False
    assert "exceeds the recommended maximum" in warning
```

## テストカバレッジ

### 現在のカバレッジ

| モジュール | カバレッジ | 未カバー行数 |
|:----------|:----------|:-----------|
| `date_utils.py` | 100% | 0 |
| `models.py` | 100% | 0 |
| `config.py` | 90% | 5 |
| `scheduler.py` | 88% | 5 |
| `slack_client.py` | 88% | 11 |
| `llm_client.py` | 85% | 12 |
| **全体** | **51%** | **358** |

### カバレッジ目標

- **クリティカルなモジュール**: 90%以上
  - `date_utils.py` ✅ 100%
  - `models.py` ✅ 100%
  - `config.py` ✅ 90%
  
- **ビジネスロジック**: 85%以上
  - `llm_client.py` ✅ 85%
  - `slack_client.py` ✅ 88%
  - `scheduler.py` ✅ 88%

## テストされる機能

### 1. 日付処理（`test_date_utils.py`）

#### 日付フォーマットの解析
- ✅ YYYY-MM-DD形式
- ✅ MM-DD-YYYY形式
- ✅ YYYY/MM/DD形式
- ✅ MM/DD/YYYY形式
- ✅ YYYYMMDD形式
- ✅ 無効な日付フォーマットのエラーハンドリング

#### 日付範囲の解析
- ✅ 単一日付
- ✅ " to "区切り
- ✅ ":"区切り
- ✅ ".."区切り
- ✅ "~"区切り

#### バリデーション
- ✅ 有効な日付範囲
- ✅ 30日を超える範囲（警告）
- ✅ 未来の日付（エラー）
- ✅ 1年以上前の日付（警告）

#### URL生成
- ✅ /login/KEY形式からの変換
- ✅ ?sha_key=KEY形式の処理
- ✅ 既存の日付パラメータの置換
- ✅ 無効なURL形式のエラーハンドリング

### 2. 設定管理（`test_config.py`）

- ✅ YAMLファイルからの設定読み込み
- ✅ 環境変数の読み込み
- ✅ 必須環境変数の検証
- ✅ デフォルト値の適用
- ✅ 設定ファイルが存在しない場合の処理

### 3. データモデル（`test_models.py`）

- ✅ Paper, TeaserFigure, PaperRelevanceの作成
- ✅ デフォルト値の適用
- ✅ ネストされたモデルの構造
- ✅ フィールドのバリデーション

### 4. LLMクライアント（`test_llm_client.py`）

- ✅ Abstract翻訳
- ✅ セクション要約生成
- ✅ arXiv HTML取得
- ✅ PDFへのリダイレクト処理
- ✅ APIエラーハンドリング
- ✅ 論文の完全処理ワークフロー

### 5. Slackクライアント（`test_slack_client.py`）

- ✅ 接続テスト
- ✅ メインメッセージの投稿
- ✅ スレッド内の要約投稿
- ✅ 画像アップロード
- ✅ 設定によるフィルタリング
- ✅ エラーハンドリング

### 6. スケジューラー（`test_scheduler.py`）

- ✅ 時刻の解析
- ✅ タスクのスケジュール登録
- ✅ 平日のみ実行
- ✅ 全日実行

## 新しいテストの追加

### テストファイルの作成

新しいモジュールをテストする場合は、`tests/`ディレクトリに`test_<module_name>.py`という名前でファイルを作成します。

```python
"""Tests for new_module."""

import pytest
from src.new_module import NewClass


class TestNewClass:
    """Tests for NewClass."""
    
    def test_basic_functionality(self):
        """Test basic functionality."""
        obj = NewClass()
        assert obj.method() == expected_result
    
    def test_error_handling(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            obj = NewClass(invalid_param)
```

### フィクスチャの使用

共通のテストデータやモックは`tests/conftest.py`にフィクスチャとして定義します。

```python
@pytest.fixture
def sample_data():
    """Sample data for tests."""
    return {
        "key": "value"
    }

def test_with_fixture(sample_data):
    """Test using fixture."""
    assert sample_data["key"] == "value"
```

### マーカーの追加

テストにマーカーを追加して分類します。

```python
@pytest.mark.unit
def test_unit_test():
    """Unit test."""
    pass

@pytest.mark.integration
def test_integration_test():
    """Integration test."""
    pass

@pytest.mark.slow
def test_slow_test():
    """Slow running test."""
    pass
```

## トラブルシューティング

### テストが失敗する場合

1. **環境変数の問題**
   - `conftest.py`の`reset_env`フィクスチャが正しく動作しているか確認
   - テスト内で環境変数を明示的に設定

2. **モックの問題**
   - モックが正しくパッチされているか確認
   - `pytest-mock`を使用してモックを管理

3. **非同期処理の問題**
   - Playwrightなどの非同期処理は適切にモック

### カバレッジが低い場合

1. **未テストのコードパスを特定**
   ```bash
   uv run pytest --cov=src --cov-report=term-missing
   ```

2. **エラーハンドリングのテストを追加**
   - 例外が発生するケース
   - 境界条件
   - エッジケース

3. **統合テストを追加**
   - 複数のモジュールが連携するシナリオ

## ベストプラクティス

1. **テストは独立させる**: 各テストは他のテストに依存しない
2. **明確な命名**: テスト名から何をテストしているか分かるようにする
3. **AAA パターン**: Arrange（準備）、Act（実行）、Assert（検証）
4. **モックを適切に使用**: 外部依存はモックして高速化
5. **境界条件をテスト**: 正常系だけでなく異常系もテスト
6. **ドキュメント**: 複雑なテストにはdocstringで説明を追加

## 継続的インテグレーション

GitHub Actionsなどを使用して、プッシュ時に自動的にテストを実行できます。

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv pip install -r requirements.txt
      - name: Run tests
        run: uv run pytest --cov=src
```

## まとめ

このテストスイートは、Scholar Inbox Slack Botの品質を保証し、リファクタリングや新機能追加を安全に行うための基盤となります。テストを継続的に追加・更新して、カバレッジを向上させていきましょう。
