import os
import discord
import traceback
from pymongo import MongoClient
from dotenv import load_dotenv
from discord.ext import commands
from services.response_service import response_message, response_join_message
from services.error_service import send_error_message
from services.mongo_adapter import MongoAdapter
import json

load_dotenv()

discord_key = os.environ["DISCORD_KEY"]
allowed_channels = {}
if os.environ["ENVIRONMENT"] == "development":
    allowed_channels = json.loads(os.environ["ALLOWED_CHANNELS_DEV"])
else:
    allowed_channels = json.loads(os.environ["ALLOWED_CHANNELS_PROD"])

join_channel_id = int(os.environ["JOIN_CHANNEL_ID"])
intents = discord.Intents.all()
intents.message_content = True
command_prefix = "/"


class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # MongoDBに接続
        client = None
        if os.environ["ENVIRONMENT"] == "development":
            client = MongoClient(
                "localhost", 27018, username="root", password="password"
            )
        else:
            client = MongoClient(
                "mongodb+srv://user:uxwl6GjFSXPkNvZJ@cluster0.njarmyw.mongodb.net/?retryWrites=true&w=majority"
            )

        # nikechan_botという名前のデータベースを取得（なかったら勝手に作成）
        db = client.nikechan_bot
        # データベースのstatesコレクションを取得（なかったら勝手に作成、コレクション=RDBMSのテーブル）
        self.collection_states = db.states
        self.collection_chats = db.chats

        # インデックスの作成
        self.collection_states.create_index([("server_id", 1)], unique=True)
        self.collection_chats.create_index([("server_id", 1)])

    async def on_ready(self):
        print("Bot is ready.")
        print("Logged in as", self.user)
        status_message = (
            "こんにちは！AIニケです！\n何か質問があれば、お気軽にお声掛けください！"
        )
        await self.change_presence(activity=discord.Game(name=status_message))

    async def on_message(self, message):
        if message.author == self.user:
            print("Message received from self, ignoring.")
            return
        try:
            if message.content.startswith(command_prefix):
                command_name = message.content[len(command_prefix) :].split(" ", 1)[0]
                if not self.get_command(command_name):
                    # コマンドが存在しない場合の処理
                    return
            elif (
                not message.content.startswith(command_prefix)
                and message.channel.id in allowed_channels.values()
            ):
                await response_message(self, message)
            elif message.channel.id == join_channel_id:
                await response_join_message(self, message)

            await super().on_message(message)
        except Exception as e:
            print("Error:", e)
            traceback.print_exc()
            await send_error_message(client, message, e)

    async def on_command_error(self, ctx, error):
        orig_error = getattr(error, "original", error)
        error_msg = "".join(
            traceback.TracebackException.from_exception(orig_error).format()
        )
        await ctx.send(error_msg)


client = MyBot(command_prefix=command_prefix, intents=intents, heartbeat_timeout=60.0)


@client.command(name="base", description="通常のニケちゃんで返答します")
async def base(ctx):
    await response_message(ctx.bot, ctx.message, "base")


client.run(discord_key)
