import asyncio
import discord
import os
from dotenv import load_dotenv

load_dotenv()

voicevox_key = os.environ['VOICEVOX_KEY']

async def play_voice(message, text):
    if message.guild.voice_client:
        # Replace new line
        text = text.replace('\n', '。')

        mp3url = 'services/system_messages/ダウンロード.wav'
        print(mp3url)
        while message.guild.voice_client.is_playing():
            await asyncio.sleep(0.5)
        source = await discord.FFmpegOpusAudio.from_probe(mp3url)
        message.guild.voice_client.play(source)
