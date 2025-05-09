# nikechan-discord

DiscordボットのAIニケちゃん（AITuber）のリポジトリです。OpenAIのAssistants APIを活用した会話型AIボットで、Discordサーバー内でユーザーとの自然な対話を実現します。

## 機能概要

- OpenAIのAssistants APIを使用した自然な会話機能
- 画像生成・説明機能（DALL-E、GPT-4 Vision）
- Web検索機能（WebPilot API、SerpAPI）
- 会話履歴の保存と文脈理解
- YouTubeチャンネル監視と通知機能
- VOICEVOXを使用した音声出力機能

## 技術スタック

- Python 3.x
- discord.py
- OpenAI API（GPT-4、GPT-3.5-turbo、DALL-E）
- MongoDB（会話履歴保存）
- Supabase（状態管理）

## 処理フロー

Discordでの入力から出力までの処理フローは以下の通りです：

### 1. メッセージ受信（main.py）

1. ユーザーがDiscordチャンネルでメッセージを送信
2. `on_message`イベントハンドラがメッセージを受信
3. 以下の条件でメッセージを処理：
   - コマンドの場合：対応するコマンド処理を実行
   - 許可されたチャンネルでの通常メッセージ：`response_message`関数を呼び出し
   - 参加チャンネルでのメッセージ：`response_join_message`関数を呼び出し

### 2. レスポンス判定（response_service.py）

1. サーバーIDから状態を取得または初期化
2. モデレーションチェック実施
3. メッセージ内容を整形
4. 以下の条件で応答が必要かを判断：
   - ボットへのリプライの場合：応答必要
   - ボットへのメンションの場合：応答必要
   - その他の場合：`judge_if_i_response`関数で判定

### 3. OpenAI API呼び出し（openai_service.py）

1. 添付ファイル処理：
   - 画像：一時保存して処理
   - その他ファイル：OpenAI APIにアップロード
2. スレッド管理：
   - 既存スレッドがある場合：更新
   - ない場合：新規作成
3. アシスタント実行：
   - システムメッセージ設定
   - モデル選択（メッセージ数に応じてGPT-4またはGPT-3.5-turbo）
   - 関数呼び出し処理

### 4. 外部機能連携（function_calling_service.py）

必要に応じて以下の外部機能を呼び出し：
1. Web検索（WebPilot API、SerpAPI）
2. 画像説明（GPT-4 Vision）
3. 画像生成（DALL-E）

### 5. レスポンス生成と送信

1. OpenAIからのレスポンスを取得
2. Discordチャンネルにメッセージを送信
3. 会話履歴を更新（最新5件を保持）
4. 状態をSupabaseに保存

### 6. エラー処理

エラー発生時：
1. エラーログを出力
2. エラーメッセージをDiscordに送信

## 設定ファイル

システムメッセージとキャラクター設定：
- `system_base.json`：基本的なキャラクター設定
- `system_mesugaki.json`：生意気キャラ設定
- `system_oji.json`：おじさんキャラ設定
- `response_message.txt`：レスポンステンプレート
- `judge_if_i_response.txt`：応答判定ロジック

## 環境変数

必要な環境変数：
- `DISCORD_KEY`：Discordボットトークン
- `OPENAI_API_KEY`：OpenAI APIキー
- `ALLOWED_CHANNELS_DEV`/`ALLOWED_CHANNELS_PROD`：許可チャンネルID
- `JOIN_CHANNEL_ID`：参加通知チャンネルID
- `WEBPILOT_API_KEY`：WebPilot APIキー（Web検索用）
- `SUPABASE_URL`/`SUPABASE_KEY`：Supabase接続情報

## セットアップ

```bash
# リポジトリのクローン
git clone https://github.com/tegnike/nikechan-discord.git
cd nikechan-discord

# 依存関係のインストール
pip install -r requirements.txt

# .envファイルの作成
cp .env.example .env
# .envファイルに必要な環境変数を設定

# 実行
python main.py
```

## デプロイ

Procfileが含まれているため、Herokuなどのプラットフォームに簡単にデプロイできます。

```bash
# Herokuへのデプロイ例
heroku create
git push heroku main
```

## ライセンス

このプロジェクトは[MITライセンス](LICENSE)の下で公開されています。
