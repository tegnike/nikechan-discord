import discord
import os
from datetime import datetime, timedelta
from pytz import timezone
from langchain.memory import ChatMessageHistory
from openai_service import get_openai_response, judge_if_i_response, get_join_response

intents = discord.Intents.all()
discord_key = os.environ['DISCORD_KEY']
allowed_channels = [1090678631489077331, 1133743935727091773]
join_channel_id = 1134007804244529212
master_id = 576031815945420812

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.states = {}

    async def on_ready(self):
        print('Bot is ready.')
        print('Logged in as', self.user)

    async def on_message(self, message):
        if message.channel.id in allowed_channels:
            self.response_message(message)
        elif message.channel.id == join_channel_id:
            self.response_join_message(message)

    async def response_message(self, message):
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


        need_response = False
        if message.reference is not None:
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
        state["history"].add_user_message(auther_name + ": " + message.content)
        print("User:", message.content)

        print("AI should response?:", need_response)

        # 応答が必要な場合
        if need_response:
            # OpenAIによる応答生成
            model_name = "gpt-4" if state["count"] <= 20 else "gpt-3.5-turbo"
            response = get_openai_response(state["history"], model_name)
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

client = MyClient(intents=intents)
client.run(discord_key)
