
import os
import discord
import traceback
from pymongo import MongoClient
from dotenv import load_dotenv
from discord.ext import commands
from services.response_service import response_message, response_join_message
from services.error_service import send_error_message

load_dotenv()

discord_key = os.environ['DISCORD_KEY']
allowed_channels = {}
if os.environ['ENVIRONMENT'] == 'development':
    allowed_channels = { 'CryptoJK': 1090678631489077331 }
else:
    allowed_channels = {
        'AITuberゲーム部': 1134007804244529212,
        'VTuberDAO': 1133743935727091773,
        'CryptoJK音声': 1090678631489077333,
        'AITuberゲーム部音声': 1114285942375718986,
        'VTuberDAO音声': 1135457812982530068,
        'AI画像（わど）': 1140955884885917757,
        'Little Girl Warriors': 1079634489317281812,
        'ExC': 1126801372533243924,
        'CryptoM': 1143119685957734470
    }
# CryptoJK音声, AITuberゲーム部音声, VTuberDAO音声
allowed_voice_channels = [1090678631489077333, 1114285942375718986, 1135457812982530068]
join_channel_id = 1052887374239105032
intents = discord.Intents.all()
intents.message_content = True
command_prefix='/'

class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # MongoDBに接続
        client = None
        if os.environ['ENVIRONMENT'] == 'development':
            client = MongoClient('localhost', 27018, username='root', password='password')
        else:
            client = MongoClient('mongodb+srv://user:uxwl6GjFSXPkNvZJ@cluster0.njarmyw.mongodb.net/?retryWrites=true&w=majority')

        # nikechan_botという名前のデータベースを取得（なかったら勝手に作成）
        db = client.nikechan_bot
        # データベースのstatesコレクションを取得（なかったら勝手に作成、コレクション=RDBMSのテーブル）
        self.collection_states = db.states
        self.collection_chats = db.chats

    async def on_ready(self):
        print('Bot is ready.')
        print('Logged in as', self.user)
        status_message = "こんにちは！AITuberのニケです！\n何か質問があれば、お気軽にお声掛けください！\n\n音声：VOICEVOX 小夜/SAYO"
        await self.change_presence(activity=discord.Game(name=status_message))

    async def on_message(self, message):
        if message.author == self.user:
            print('Message received from self, ignoring.')
            return
        try:
            if message.content.startswith(command_prefix):
                command_name = message.content[len(command_prefix):].split(' ', 1)[0]
                if not self.get_command(command_name):
                    # コマンドが存在しない場合の処理
                    return
            elif not message.content.startswith(command_prefix) and message.channel.id in allowed_channels.values():
                await response_message(self, message)
            elif message.channel.id == join_channel_id:
                await response_join_message(self, message)

            await super().on_message(message)
        except Exception as e:
            print("Error:", e)
            traceback.print_exc()
            await send_error_message(client, message, e)

    async def on_command_error(self, ctx, error):
        orig_error = getattr(error, 'original', error)
        error_msg = ''.join(traceback.TracebackException.from_exception(orig_error).format())
        await ctx.send(error_msg)

client = MyBot(command_prefix=command_prefix, intents=intents, heartbeat_timeout=60.0)

@client.command(name='base', description="通常のニケちゃんで返答します")
async def base(ctx):
    await response_message(ctx.bot, ctx.message, 'base')

client.run(discord_key)
