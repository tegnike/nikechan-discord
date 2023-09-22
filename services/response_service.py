import re
from datetime import datetime
from pytz import timezone
from services.openai_service import send_openai_response, judge_if_i_response
from services.voicevox_service import play_voice
from services.moderation_service import check_moderation
from services.select_random_message_service import select_random_message

master_id = 576031815945420812
allowed_voice_channels = [1090678631489077333, 1114285942375718986, 1135457812982530068]

async def response_message(self, message, type=None):
    # サーバーID取得
    server_id = message.guild.id

    # サーバーIDから状態を取得、なければ初期化
    state = self.collection_states.find_one({"server_id": server_id})
    if state == None:
        state = {
            "server_id": server_id,
            "history": [],
            "count": 0,
            "current_date": datetime.now(timezone('Europe/Warsaw')).date(),
            "type": "base",
            "last_message": datetime.now(timezone('Europe/Warsaw')),
            "is_daily_limit": False,
            "is_monthly_limit": False,
        }
        to_mongo(state)
        self.collection_states.insert_one(state)
    from_mongo(state)

    # 日付が変わったらカウントをリセット
    new_date = datetime.now(timezone('Europe/Warsaw')).date()
    if new_date > state["current_date"]:
        state["count"] = 0
        state["current_date"] = new_date 

    # 自分のメッセージは無視 または 50件以上のメッセージは無視
    if message.author == self.user:
        print('Message received from self, ignoring.')
        return
    if state["count"] >= 100:
        if state["count"] == 100:
            await message.channel.send("[固定応答]設定上限に達したため、本日の応答は終了します。")
        print('Message limit.')
        return
    if await check_moderation(message):
        print('Moderation True.')
        return

    # auther_nameを取得
    auther_name = ''
    if master_id == message.author.id:
        auther_name = 'マスター'
    elif hasattr(message.author, 'nick') and message.author.nick:
        auther_name = message.author.nick
    else:
        auther_name = message.author.name
    print('Message received from', auther_name, ':', message.content)

    # タイプを切り替え
    if type != None:
        state["type"] = type
    elif (datetime.now(timezone('Europe/Warsaw')) - state["last_message"]).days >= 1:
        state["type"] = 'base'
    else:
        state["type"] = state["type"]

    need_response = False
    if type != None:
        state["type"] = type
        need_response = True
        print("Switch type:", type)
    elif message.reference is not None:
        # bot宛のリプライであるかを確認
        referenced_message = await message.channel.fetch_message(message.reference.message_id)
        need_response = referenced_message.author == self.user
        # リプライに反応させるようにリプライメッセージを履歴に追加
        print("Referenced message:", referenced_message.content)
        state["history"].append({"role": "assistant", "content": referenced_message.content})
    elif self.user in message.mentions:
        # bot宛のメンションであるかを確認
        need_response = True
    else:
        # 会話歴から次に自分が回答すべきかを判定
        need_response = await judge_if_i_response(message, state["history"])

    # メッセージ整形
    message_content = re.sub(r'<@!?\d+>', '', message.content)

    # 日本時間の現在時刻を'%Y/%m/%d %H:%M'形式で取得
    now = datetime.now(timezone('Asia/Tokyo')).strftime('%Y/%m/%d %H:%M')

    # ユーザーメッセージを会話履歴に追加
    state["history"].append({"role": "user", "content": f"{auther_name}({now}): {message_content}"})
    print("User:", message_content)

    print("AI should response?:", need_response)

    # 応答が必要な場合
    if need_response:
        # 会話歴は常に15件に保つ
        state["history"] = state["history"][-15:]
        print("history:", state["history"])

        # OpenAIによる応答生成
        model_name = "gpt-3.5-turbo"
        # model_name = "gpt-4" if state["count"] <= 20 else "gpt-3.5-turbo"
        response = await send_openai_response(message, state["history"], model_name, state["type"])
        # # 音声メッセージ
        # if message.channel.id in allowed_voice_channels:
        #     print("Play Voice:", response)
        #     await play_voice(message, response)

        state["last_message"] = datetime.now(timezone('Europe/Warsaw'))

        # if state["count"] == 20:
        #     # 20件目のメッセージを送信したら、モデルをGPT-3.5に切り替える
        #     await message.channel.send("[固定応答]設定上限に達したため、モデルをGPT-4からGPT-3.5に切り替えます。")

        state["count"] += 1
        print('Message send completed.')

        self.collection_chats.insert_one({
            "server_id": server_id,
            "user": message_content,
            "assistant": response
        })
    else:
        print('Message was not sent.')

    # 状態を更新
    to_mongo(state)
    self.collection_states.update_one({"server_id": server_id}, {"$set": state})

async def response_join_message(self, message):
    if message.mentions:
        user = message.mentions[0]
        # user_nameを取得
        user_name = ''
        if user.nick:
            user_name = user.nick
        else:
            user_name = user.name
        print('User joined', ':', user_name)

        # メッセージを送信
        await message.channel.send(select_random_message('join_messages').replace("XXXXX", user_name))

        print('Join message completed.')
    else:
        print('Nobady joined.')

# MongoDBに保存する用にデータを変換
def to_mongo(state):
    state["current_date"] = state["current_date"].strftime('%Y-%m-%d')
    state["last_message"] = state["last_message"].strftime('%Y-%m-%d %H:%M:%S')

# MongoDBのデータをpythonで使用できるように変換
def from_mongo(state):
    state["current_date"] = datetime.strptime(state["current_date"], '%Y-%m-%d').date()
    state["last_message"] = datetime.strptime(state["last_message"], '%Y-%m-%d %H:%M:%S').astimezone(timezone('Europe/Warsaw'))
