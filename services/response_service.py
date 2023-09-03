import json, random
from datetime import datetime
from pytz import timezone
from langchain.memory import ChatMessageHistory
from services.openai_service import get_openai_response, judge_if_i_response
from services.voicevox_service import play_voice
from langchain.schema import (
    SystemMessage,
    HumanMessage
)

master_id = 576031815945420812
allowed_voice_channels = [1090678631489077333, 1114285942375718986, 1135457812982530068]

async def response_message(self, message, type=None):
    # サーバーID取得
    server_id = message.guild.id

    # サーバーIDから状態を取得、なければ初期化
    state = self.mongo_collection.find_one({"server_id": server_id})
    if state == None:
        state = {
            "server_id": server_id,
            "history": ChatMessageHistory(),
            "count": 0,
            "current_date": datetime.now(timezone('Europe/Warsaw')).date(),
            "type": "base",
            "last_message": datetime.now(timezone('Europe/Warsaw')),
            "is_daily_limit": False,
            "is_monthly_limit": False,
        }
        to_mongo(state)
        self.mongo_collection.insert_one(state)
    from_mongo(state)

    # 日付が変わったらカウントをリセット
    new_date = datetime.now(timezone('Europe/Warsaw')).date()
    if new_date > state["current_date"]:
        state["count"] = 0
        state["current_date"] = new_date

    # 自分のメッセージは無視 または 100件以上のメッセージは無視
    if message.author == self.user:
        print('Message received from self, ignoring.')
        return
    if state["count"] > 100:
        if state["count"] == 100:
            await message.channel.send("[固定応答]設定上限に達したため、本日の応答は終了します。")
        print('Message limit.')
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
        # bot宛のメンションであるかを確認
        need_response = True
        print("Switch type:", type)
    elif message.reference is not None:
        # bot宛のリプライであるかを確認
        referenced_message = await message.channel.fetch_message(message.reference.message_id)
        need_response = referenced_message.author == self.user
        # リプライに反応させるようにリプライメッセージを履歴に追加
        print("Referenced message:", referenced_message.content)
        state["history"].add_ai_message(referenced_message.content)
    elif self.user in message.mentions:
        # bot宛のメンションであるかを確認
        need_response = True
    else:
        # 会話歴から次に自分が回答すべきかを判定
        need_response = await judge_if_i_response(state["history"])

    # ユーザーメッセージを会話履歴に追加
    state["history"].add_user_message(auther_name + ": " + message.content)
    print("User:", message.content)

    print("AI should response?:", need_response)

    # 応答が必要な場合
    if need_response:
        # OpenAIによる応答生成
        model_name = "gpt-4" if state["count"] <= 20 else "gpt-3.5-turbo"
        response = await get_openai_response(state["history"], model_name, state["type"])
        # 音声メッセージ
        if message.channel.id in allowed_voice_channels:
            print("Play Voice:", response)
            await play_voice(message, response)

        # メッセージを送信
        await message.channel.send(response)
        state["last_message"] = datetime.now(timezone('Europe/Warsaw'))

        if state["count"] == 20:
            # 20件目のメッセージを送信したら、モデルをGPT-3.5に切り替える
            await message.channel.send("[固定応答]設定上限に達したため、モデルをGPT-4からGPT-3.5に切り替えます。")

        state["count"] += 1
        print('Message send completed.')
    else:
        print('Message was not sent.')

    # 状態を更新
    to_mongo(state)
    self.mongo_collection.update_one({"server_id": server_id}, {"$set": state})

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

        # ファイルからメッセージをロード
        with open('services/scripts/join_messages', 'r') as f:
            join_messages = json.load(f)
        join_message = random.choice(join_messages)

        # メッセージを送信
        await message.channel.send(join_message.replace("XXXXX", user_name))

        print('Join message completed.')
    else:
        print('Nobady joined.')

# MongoDBに保存する用にデータを変換
def to_mongo(state):
    messages = []
    for message in state["history"].messages:
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        messages.append({
            "role": role,
            "content": message.content
        })
    state["history"] = messages

    state["current_date"] = state["current_date"].strftime('%Y-%m-%d')
    state["last_message"] = state["last_message"].strftime('%Y-%m-%d %H:%M:%S')

# MongoDBのデータをpythonで使用できるように変換
def from_mongo(state):
    history = ChatMessageHistory()
    for message in state["history"]:
        if message["role"] == "user":
            history.add_user_message(message["content"])
        else:
            history.add_ai_message(message["content"])
    state["history"] = history

    # state["current_date"] = '2023-08-25'をdate型に変換
    state["current_date"] = datetime.strptime(state["current_date"], '%Y-%m-%d').date()
    state["last_message"] = datetime.strptime(state["last_message"], '%Y-%m-%d %H:%M:%S').astimezone(timezone('Europe/Warsaw'))
