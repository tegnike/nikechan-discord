# Discord 定期通知（Cloudflare Workers）

- 20分おき（UTC）に `#AIニケちゃん` の最新ツイート（返信/リポスト除外）を取得し、twitter.py と同じ文面で Discord に通知します。
- 常時起動サーバー不要。Cron Trigger + Webhook。

## セットアップ

```bash
cd cf-worker
# 必要なら wrangler をインストール（ローカル開発用）
# npm i -g wrangler

# シークレット登録
npx wrangler secret put WEBHOOK_URL
npx wrangler secret put X_BEARER_TOKEN
# 任意（手動実行 /run?token=...）
npx wrangler secret put JOB_TOKEN
```

`wrangler.toml` の Cron は 20分おき（UTC）に設定済みです。

## 開発・デプロイ

```bash
# ローカルで Cron を模擬実行
npx wrangler dev --test-scheduled
# 別ターミナルで擬似Cronを叩く
curl "http://127.0.0.1:8787/__scheduled?cron=*/20%20*%20*%20*%20*"

# デバッグ用: 手動実行
# （JOB_TOKEN を入れていれば）
curl "http://127.0.0.1:8787/run?token=<JOB_TOKEN>"

# デプロイ
npx wrangler deploy
# ログ
npx wrangler tail

## Supabase 連携

- 用途: 取得済みツイートを保存し、直近30分に作成されたレコードの投稿IDを参照して重複送信を防ぎます。
- 環境変数（Secrets 推奨）:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`（Service Role キー）

```bash
cd cf-worker
npx wrangler secret put SUPABASE_URL
npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY
```

### テーブル定義（例: public.tweet_logs）

以下のSQLをSupabaseのSQL Editorで実行してください。

```sql
-- UUID主キーを使用し、post_idは一意制約で重複保存を防止します
create extension if not exists pgcrypto; -- gen_random_uuid()

create table if not exists public.tweet_logs (
  id uuid primary key default gen_random_uuid(),
  post_id text not null unique,
  user_id text not null,
  username text not null,
  name text not null,
  posted_at timestamptz not null,
  body text not null,
  url text not null,
  hashtag text not null,
  created_at timestamptz not null default now()
);

create index if not exists tweet_logs_created_at_idx on public.tweet_logs (created_at desc);
```

既存テーブルに `hashtag` 列を追加する場合は以下を実行:

```sql
alter table public.tweet_logs
  add column if not exists hashtag text;

-- 過去レコードを既定ハッシュタグで更新（必要に応じて）
update public.tweet_logs set hashtag = '#AIニケちゃん' where hashtag is null;

-- NOT NULL 制約を付与
alter table public.tweet_logs
  alter column hashtag set not null;
```

> 備考: Service Role Key をワーカーのシークレットとして使用します（RLSを気にせずInsert/Select可能）。漏えい防止のためリポジトリに含めないでください。

### 動作仕様（変更点）

- X API は「実行時から直近25分」のウィンドウで検索します（`start_time`/`end_time`）。
- Supabaseから「直近25分にDBで作成されたレコード」の `post_id` を取得し、同一IDのツイートは送信対象から除外します。
- 除外後のツイートのみDiscordへ送信し、DBに保存します（`post_id` 競合時はマージ）。
```

## 備考
- X API の検索クエリは `#AIニケちゃん -is:reply -is:retweet`。必要なら `-is:quote` を追加してください。
- Discord の文字数上限（2000字）に合わせて分割送信します。
- 失敗時は指数バックオフで最大3回リトライします（429/5xx/ネットワーク/タイムアウト）。
- 送信文面は `twitter.py` の print 出力を再現しています。
