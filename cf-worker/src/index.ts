// Cloudflare Worker — Discord通知（20分おき）
// - X(旧Twitter) Recent Search API から #AIニケちゃん の元ツイのみを取得
// - twitter.py の print 出力と同等の文面を Discord Webhook に投稿

type Env = {
  WEBHOOK_URL: string; // wrangler secret put WEBHOOK_URL
  JOB_TOKEN?: string;  // 任意: 手動実行用
  X_BEARER_TOKEN: string; // wrangler secret put X_BEARER_TOKEN

  // Supabase (Service Role キーを推奨)
  SUPABASE_URL: string; // wrangler secret put SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY: string; // wrangler secret put SUPABASE_SERVICE_ROLE_KEY
};

const HASHTAG = "#AIニケちゃん";

export default {
  // Cron 起動
  async scheduled(_event: ScheduledEvent, env: Env, ctx: ExecutionContext) {
    ctx.waitUntil(run(env));
  },

  // デバッグ用: 手動実行 (GET /run?token=...)
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    if (url.pathname === "/run") {
      const ok = env.JOB_TOKEN && url.searchParams.get("token") === env.JOB_TOKEN;
      if (!ok) return new Response("forbidden\n", { status: 403 });
      await run(env);
      return new Response("ok\n");
    }
    return new Response("not found\n", { status: 404 });
  },
};

async function run(env: Env): Promise<void> {
  try {
    // 直近25分ウィンドウでXから取得し、DBの直近25分で作成されたレコード(= post_id)を除外
    // X APIの制約: end_time は現在時刻の少なくとも10秒前である必要がある
    const now = Date.now();
    const endIso = new Date(now - 15 * 1000).toISOString(); // 安全側に15秒前
    const startIso = new Date(new Date(endIso).getTime() - 25 * 60 * 1000).toISOString();

    const [existingIds, fetched] = await Promise.all([
      getRecentPostIds(env, startIso),
      fetchTweetsWindow(env, startIso, endIso),
    ]);

    const fresh = fetched.filter((tw) => !existingIds.has(tw.post_id));

    if (fresh.length === 0) {
      console.log("no new tweets to send");
      return;
    }

    // 各ツイートごとに URL のみをDiscordに投稿
    for (const t of fresh) {
      const urlOnly = t.url;
      if (urlOnly) {
        await sendDiscord(env, urlOnly);
      }
    }

    // 保存（post_id で重複時はupsert想定）
    await saveTweets(env, fresh);
  } catch (e) {
    console.error("run error", e);
    throw e; // Workers ログで可視化
  }
}

// X から 30分ウィンドウで取得し、保存・通知に使う最小情報へ整形
async function fetchTweetsWindow(env: Env, startIso: string, endIso: string): Promise<DbTweet[]> {
  const token = env.X_BEARER_TOKEN;
  if (!token) throw new Error("環境変数 X_BEARER_TOKEN が未設定です");

  const url = new URL("https://api.x.com/2/tweets/search/recent");
  const query = `${HASHTAG} -is:reply -is:retweet`; // 必要なら -is:quote 追加
  const params = new URLSearchParams({
    query,
    max_results: "100", // 25分の範囲で取り切る想定
    sort_order: "recency",
    "tweet.fields": "created_at,lang,public_metrics,author_id,source",
    expansions: "author_id",
    "user.fields": "username,name,profile_image_url,verified",
    start_time: startIso,
    end_time: endIso,
  });
  url.search = params.toString();

  const res = await safeFetch(
    url.toString(),
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
    20000,
    5, // 429 に備えて少し多めにリトライ
    800,
  );

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`X API error: ${res.status} ${text}`);
  }

  const data: any = await res.json();
  const usersArr: any[] = data?.includes?.users ?? [];
  const users = new Map<string, any>();
  for (const u of usersArr) users.set(u.id, u);

  const tweets: any[] = data?.data ?? [];

  const mapped: DbTweet[] = tweets.map((t) => {
    const user = users.get(t.author_id) ?? {};
    const uname = user?.username ?? "";
    const id = t?.id ?? "";
    return {
      post_id: id,
      user_id: String(t?.author_id ?? ""),
      username: uname,
      name: user?.name ?? "",
      posted_at: t?.created_at ?? "",
      body: String(t?.text ?? ""),
      url: `https://x.com/${uname}/status/${id}`,
      hashtag: HASHTAG,
      // created_at はDB側で now() を使用
      metrics: {
        like: t?.public_metrics?.like_count ?? 0,
        rt: t?.public_metrics?.retweet_count ?? 0,
        reply: t?.public_metrics?.reply_count ?? 0,
      },
    };
  });

  return mapped;
}

// Discordへ投げるための整形（twitter.pyの出力に準拠）
function formatTweetsForDiscord(tweets: DbTweet[]): string {
  const lines: string[] = [];
  tweets.forEach((t, idx) => {
    const num = String(idx + 1).padStart(2, "0");
    const textNoNewline = t.body.replace(/\n/g, " ");
    const m = t.metrics ?? { like: 0, rt: 0, reply: 0 };
    lines.push(
      `${num}. @${t.username} (${t.name})`,
      `    ${t.posted_at}  ❤️${m.like} 🔁${m.rt} 💬${m.reply}`,
      `    ${textNoNewline}`,
      `    ${t.url}`,
      "",
    );
  });
  return lines.join("\n");
}

async function sendDiscord(env: Env, content: string): Promise<void> {
  // Discord content は最大 2000 文字（安全側で 1900 に分割）
  const chunks = splitForDiscord(content, 1900);
  for (const part of chunks) {
    const body = { content: part };
    const res = await safeFetch(
      env.WEBHOOK_URL,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
      15000,
    );

    if (res.status === 429) {
      const retryAfter = res.headers.get("retry-after");
      throw new Error(`Discord 429; retry-after=${retryAfter ?? "n/a"}`);
    }
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`Discord error: ${res.status} ${text}`);
    }
  }
}

function splitForDiscord(text: string, maxLen: number): string[] {
  if (text.length <= maxLen) return [text];
  const parts: string[] = [];
  const blocks = text.split("\n\n"); // ツイートごとに区切られている前提
  let buf = "";
  for (const b of blocks) {
    const candidate = buf ? `${buf}\n\n${b}` : b;
    if (candidate.length <= maxLen) {
      buf = candidate;
    } else {
      if (buf) parts.push(buf);
      if (b.length <= maxLen) {
        buf = b;
      } else {
        // 1ブロックが長すぎる場合は強制分割
        for (let i = 0; i < b.length; i += maxLen) {
          parts.push(b.slice(i, i + maxLen));
        }
        buf = "";
      }
    }
  }
  if (buf) parts.push(buf);
  return parts;
}

/** fetch + タイムアウト + リトライ（ネットワーク/5xx/429） */
async function safeFetch(
  url: string,
  init: RequestInit,
  timeoutMs: number,
  retries = 3,
  baseDelayMs = 500,
): Promise<Response> {
  let lastErr: unknown = undefined;
  let lastStatus: number | undefined = undefined;
  let lastHeaders: Headers | undefined = undefined;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const ctrl = new AbortController();
    const tid = setTimeout(() => ctrl.abort("timeout"), timeoutMs);
    try {
      const res = await fetch(url, { ...init, signal: ctrl.signal });
      lastStatus = res.status;
      lastHeaders = res.headers;
      if (res.ok) return res;
      if (res.status === 429 || res.status >= 500) {
        lastErr = new Error(`status ${res.status}`);
      } else {
        return res; // 4xxはそのまま返す
      }
    } catch (e) {
      lastErr = e; // タイムアウト/ネットワーク
    } finally {
      clearTimeout(tid);
    }

    // Backoff（429 の場合はヘッダを優先）
    let delay = baseDelayMs * Math.pow(2, attempt);
    if (lastStatus === 429 && lastHeaders) {
      const retryAfter = lastHeaders.get("retry-after");
      const reset = lastHeaders.get("x-rate-limit-reset");
      if (reset) {
        const resetSec = Number(reset);
        if (!Number.isNaN(resetSec)) {
          const until = resetSec * 1000 - Date.now() + 1000; // +1s バッファ
          if (until > 0) delay = until;
        }
      } else if (retryAfter) {
        const ra = Number(retryAfter);
        if (!Number.isNaN(ra)) delay = Math.max(delay, ra * 1000);
      }
      // 上限（開発時の過度な待機を防ぐ）。必要に応じて調整
      delay = Math.min(delay, 120_000);
    }
    await sleep(delay);
  }
  if (lastErr) throw lastErr;
  return fetch(url, init);
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

// ---------- Supabase 連携 ----------

type DbTweet = {
  post_id: string;
  user_id: string;
  username: string;
  name: string;
  posted_at: string; // ISO8601
  body: string;
  url: string;
  hashtag: string;
  metrics?: { like: number; rt: number; reply: number };
};

const SUPABASE_TABLE = "tweet_logs"; // public.tweet_logs を想定

async function getRecentPostIds(env: Env, sinceIso: string): Promise<Set<string>> {
  requireSupabaseEnv(env);
  const url = new URL(`${env.SUPABASE_URL}/rest/v1/${SUPABASE_TABLE}`);
  const qs = new URLSearchParams();
  qs.set("select", "post_id,created_at");
  qs.set("created_at", `gte.${sinceIso}`); // 直近25分に作成されたレコード
  url.search = qs.toString();

  const res = await safeFetch(
    url.toString(),
    {
      headers: supabaseHeaders(env),
    },
    15000,
  );
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Supabase select error: ${res.status} ${text}`);
  }
  const rows: Array<{ post_id: string }> = await res.json();
  return new Set(rows.map((r) => r.post_id).filter(Boolean));
}

async function saveTweets(env: Env, tweets: DbTweet[]): Promise<void> {
  if (tweets.length === 0) return;
  requireSupabaseEnv(env);
  const url = new URL(`${env.SUPABASE_URL}/rest/v1/${SUPABASE_TABLE}`);
  url.searchParams.set("on_conflict", "post_id");

  // DBに保存する形に射影
  const payload = tweets.map((t) => ({
    post_id: t.post_id,
    user_id: t.user_id,
    username: t.username,
    name: t.name,
    posted_at: t.posted_at,
    body: t.body,
    url: t.url,
    hashtag: t.hashtag,
  }));

  const res = await safeFetch(
    url.toString(),
    {
      method: "POST",
      headers: {
        ...supabaseHeaders(env),
        "Content-Type": "application/json",
        // 既存post_idと競合時はmerge（重複保存を避ける）
        Prefer: "resolution=merge-duplicates,return=minimal",
      } as any,
      body: JSON.stringify(payload),
    },
    20000,
  );
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Supabase upsert error: ${res.status} ${text}`);
  }
}

function supabaseHeaders(env: Env): HeadersInit {
  return {
    apikey: env.SUPABASE_SERVICE_ROLE_KEY,
    Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
    Accept: "application/json",
  };
}

function requireSupabaseEnv(env: Env) {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
    throw new Error("Supabase 環境変数 (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) が未設定です");
  }
}
