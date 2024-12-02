import re
from datetime import datetime
from pytz import timezone
from openai import OpenAI
from services.openai_service import send_openai_response, judge_if_i_response
from services.moderation_service import check_moderation
from services.select_random_message_service import select_random_message
from services.mongo_adapter import MongoAdapter

master_id = 576031815945420812
allowed_voice_channels = [1090678631489077333, 1114285942375718986, 1135457812982530068]
client = OpenAI()


async def response_message(self, message):
    # MongoAdapterのインスタンス化
    mongo_adapter = MongoAdapter(self.collection_states, self.collection_chats)

    # サーバーID取得
    server_id = message.guild.id

    # サーバーIDから状態を取得、なければ初期化
    state = mongo_adapter.get_or_create_state(server_id)

    # 日付が変わったらカウントをリセット
    new_date = datetime.now(timezone("Europe/Warsaw")).date()
    if new_date > state["current_date"]:
        state["count"] = 0
        state["current_date"] = new_date

    # 100件以上のメッセージは無視
    if state["count"] >= 100:
        if state["count"] == 100:
            await message.channel.send(
                "[固定応答]設定上限に達したため、本日の応答は終了します。"
            )
            state["count"] = 101
        print("Message limit.")
        return
    if await check_moderation(message):
        print("Moderation True.")
        return

    # メッセージ整形
    message_content = re.sub(r"<@!?\d+>", "", message.content)

    # auther_nameを取得
    auther_name = ""
    if master_id == message.author.id:
        auther_name = "マスター"
    elif hasattr(message.author, "nick") and message.author.nick:
        auther_name = message.author.nick
    else:
        auther_name = message.author.name

    # デバッグ用のログ出力を追加
    print(
        f"Debug: author.id={message.author.id}, author.name={message.author.name}, author.nick={message.author.nick}"
    )

    print("Message received from", auther_name, ":", message_content)

    # 日本時間の現在時刻を'%Y/%m/%d %H:%M'形式で取得
    now = datetime.now(timezone("Asia/Tokyo")).strftime("%Y/%m/%d %H:%M")
    message_content = f"{auther_name}({now}): {message_content}"

    need_response = False
    if message.reference is not None:
        # bot宛のリプライであるかを確認
        referenced_message = await message.channel.fetch_message(
            message.reference.message_id
        )
        need_response = referenced_message.author == self.user
        # リプライに反応させるようにリプライメッセージを履歴に追加
        print("Referenced message:", referenced_message.content)
        referenced_message_content = (
            f"{auther_name}({now}): {referenced_message.content}"
        )
        message_content = (
            f"AIであるあなたの発言: {referenced_message_content}\n{message_content}"
        )
    elif self.user in message.mentions:
        # bot宛のメンションであるかを確認
        need_response = True
    else:
        # 会話歴から次に自分が回答すべきかを判定
        need_response = await judge_if_i_response(message, state["messages_for_judge"])

    state["messages_for_history"].append(message_content)
    state["messages_for_judge"].append({"role": "user", "content": message_content})

    print("AI should response?:", need_response)

    # 応答が必要な場合
    if need_response:
        # OpenAIによる応答生成
        model_name = "gpt-3.5-turbo"
        model_name = "gpt-4o" if state["count"] <= 20 else "gpt-3.5-turbo"
        response, thread_id = await send_openai_response(
            message, state["messages_for_history"], model_name, state["thread_id"]
        )

        state["messages_for_judge"].append({"role": "assistant", "content": response})
        state["thread_id"] = thread_id

        # if state["count"] == 20:
        #     # 20件目のメッセージを送信したら、モデルをGPT-3.5に切り替える
        #     await message.channel.send("[固定応答]設定上限に達したため、モデルをGPT-4からGPT-3.5に切り替えます。")

        state["count"] += 1
        print("Message send completed.")

        # 会話歴は常に5件に保つ
        state["messages_for_judge"] = state["messages_for_judge"][-5:]
        state["messages_for_history"].clear()

        mongo_adapter.save_chat(server_id, message_content, response)
    else:
        print("Message was not sent.")

    # 状態を更新
    mongo_adapter.update_state(server_id, state)


async def response_join_message(self, message):
    if message.mentions:
        user_id = message.mentions[0].id  # メンションされたユーザーのIDを取得
        member = message.guild.get_member(
            user_id
        )  # IDからサーバー内のMemberオブジェクトを取得
        if member:
            # user_nameを取得
            user_name = member.nick if member.nick else member.name
            print("User joined", ":", user_name)

            # メッセージを送信
            await message.channel.send(
                select_random_message("join_messages").replace("XXXXX", user_name)
            )

            print("Join message completed.")
        else:
            print("Member not found.")
    else:
        print("Nobody joined.")
