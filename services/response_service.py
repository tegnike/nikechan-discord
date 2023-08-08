from datetime import datetime
from pytz import timezone
from langchain.memory import ChatMessageHistory
from services.openai_service import get_openai_response, judge_if_i_response, get_join_response
from services.voicevox_service import play_voice

master_id = 576031815945420812
allowed_voice_channels = [1090678631489077333, 1114285942375718986, 1135457812982530068]

async def response_message(self, message, type=None):
    # サーバーID取得
    server_id = message.guild.id

    # サーバーIDがなければ初期化
    if server_id not in self.states:
        self.states[server_id] = {
            "history": ChatMessageHistory(),
            "count": 0,
            "current_date": datetime.now(timezone('Europe/Warsaw')).date(),
        }

    # サーバーIDから状態を取得
    state = self.states[server_id]

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
    elif message.author.nick:
        auther_name = message.author.nick
    else:
        auther_name = message.author.name
    print('Message received from', auther_name, ':', message.content)

    history = state["history"]

    need_response = False
    if type != None:
        # bot宛のメンションであるかを確認
        need_response = True
        history = ChatMessageHistory()
        print("Use type:", type)
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
        need_response = judge_if_i_response(state["history"])

    # ユーザーメッセージを会話履歴に追加
    history.add_user_message(auther_name + ": " + message.content)
    print("User:", message.content)

    print("AI should response?:", need_response)

    # 応答が必要な場合
    if need_response:
        # OpenAIによる応答生成
        model_name = "gpt-4" if state["count"] <= 20 else "gpt-3.5-turbo"
        response = get_openai_response(history, model_name, type)
        # 音声メッセージ
        if message.channel.id in allowed_voice_channels:
            print("Play Voice:", response)
            await play_voice(message, response)

        # メッセージを送信
        await message.channel.send(response)

        if state["count"] == 20:
            # 20件目のメッセージを送信したら、モデルをGPT-3.5に切り替える
            await message.channel.send("[固定応答]設定上限に達したため、モデルをGPT-4からGPT-3.5に切り替えます。")

        state["count"] += 1
        print('Message send completed.')
    else:
        print('Message was not sent.')

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

        response = get_join_response(user_name)
        # メッセージを送信
        await message.channel.send(response)

        print('Join message completed.')
    else:
        print('Nobady joined.')
