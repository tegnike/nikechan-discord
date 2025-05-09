from datetime import datetime
from supabase import create_client
from openai import OpenAI
import os


class SupabaseAdapter:
    def __init__(self):
        supabase_url = os.environ["SUPABASE_URL"]
        supabase_key = os.environ["SUPABASE_KEY"]
        self.supabase = create_client(supabase_url, supabase_key)
        self.openai_client = OpenAI()

    def get_or_create_state(self, server_id):
        # サーバーの状態を取得
        result = (
            self.supabase.table("discord_server_states")
            .select("*")
            .eq("server_id", server_id)
            .execute()
        )

        if not result.data:
            # 新規スレッドの作成
            thread = self.openai_client.beta.threads.create()

            # 新規サーバー状態の作成
            new_state = {
                "server_id": server_id,
                "message_count": 0,
                "current_date": datetime.now().date().isoformat(),
                "is_daily_limit": False,
                "is_monthly_limit": False,
                "thread_id": thread.id,
            }
            self.supabase.table("discord_server_states").insert(new_state).execute()
            state = new_state
        else:
            state = result.data[0]

        # current_dateを文字列からdatetime.date型に変換
        state["current_date"] = datetime.strptime(
            state["current_date"], "%Y-%m-%d"
        ).date()

        # メモリ上で使用する一時的な状態を追加
        state["messages_for_history"] = []
        state["messages_for_judge"] = []

        return state

    def update_state(self, server_id, state):
        # データベースに保存する必要がある情報のみを抽出
        db_state = {
            "message_count": state["message_count"],
            "current_date": state["current_date"].isoformat(),
            "is_daily_limit": state["is_daily_limit"],
            "is_monthly_limit": state["is_monthly_limit"],
            "thread_id": state["thread_id"],
        }

        self.supabase.table("discord_server_states").update(db_state).eq(
            "server_id", server_id
        ).execute()

    def save_chat(self, server_id, user_message, assistant_message):
        # ユーザーメッセージの保存
        user_data = {
            "server_id": server_id,
            "content": user_message,
            "role": "user",
        }
        self.supabase.table("discord_messages").insert(user_data).execute()

        # アシスタントメッセージの保存
        if assistant_message:  # 応答がある場合のみ保存
            assistant_data = {
                "server_id": server_id,
                "content": assistant_message,
                "role": "assistant",
            }
            self.supabase.table("discord_messages").insert(assistant_data).execute()

    def get_recent_messages(self, server_id, limit=5):
        """
        最近のメッセージを取得（judge_if_i_responseで使用）
        """
        result = (
            self.supabase.table("discord_messages")
            .select("*")
            .eq("server_id", server_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return result.data
