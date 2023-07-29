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

        mp3url = f'https://deprecatedapis.tts.quest/v2/voicevox/audio/?text={text}&key={voicevox_key}&speaker=46&pitch=-0.02&intonationScale=1.26&speed=0.9'
        print(mp3url)
        while message.guild.voice_client.is_playing():
            await asyncio.sleep(0.5)
        source = await discord.FFmpegOpusAudio.from_probe(mp3url)
        message.guild.voice_client.play(source)
