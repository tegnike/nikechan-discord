import discord
import os
from datetime import datetime, timedelta
from pytz import timezone
from langchain.memory import ChatMessageHistory
from openai_service import get_openai_response, judge_if_i_response

intents = discord.Intents.all()
discord_key = os.environ['DISCORD_KEY']

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history = ChatMessageHistory()
        self.count = 0
        self.current_date = datetime.now(timezone('Europe/Warsaw')).date()

    async def on_ready(self):
        print('Bot is ready.')
        print('Logged in as', self.user)

    async def on_message(self, message):
        print('Message received from', message.author, ':', message.content)

        # don't respond to ourselves
        if message.author == self.user:
            print('Message received from self, ignoring.')
            return

        # ユーザーメッセージを会話履歴に追加
        self.history.add_user_message(message.author + ": " + message.content)
        print("User:", message.content)

        if judge_if_i_response(self.history):
            # Check if date has changed
            new_date = datetime.now(timezone('Europe/Warsaw')).date()
            if new_date > self.current_date:
                self.count = 0
                self.current_date = new_date

            model_name = "gpt-4" if self.count <= 20 else "gpt-3.5-turbo"
            response = get_openai_response(message.content, self.history, model_name)
            await message.channel.send(response)

            self.count += 1
            print('Message send completed.')
        else:
            print('Message not recognized.')

client = MyClient(intents=intents)
client.run(discord_key)
