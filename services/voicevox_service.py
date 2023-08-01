import asyncio
import discord
import os
import requests
from dotenv import load_dotenv

load_dotenv()

voicevox_key = os.environ['VOICEVOX_KEY']

async def play_voice(message, text):
    if message.guild.voice_client:
        # Replace new line
        text = text.replace('\n', '。')

        mp3url = f'https://deprecatedapis.tts.quest/v2/voicevox/audio/?text={text}&key={voicevox_key}&speaker=46&pitch=-0.02&intonationScale=1.26&speed=0.9'
        response = requests.get(mp3url)
        with open('audio.opus', 'wb') as f:
            f.write(response.content)

        while message.guild.voice_client.is_playing():
            await asyncio.sleep(0.5)
        source = await discord.FFmpegOpusAudio.from_probe('audio.opus')
        try:
            message.guild.voice_client.play(source)
        except discord.errors.ClientException:
            # Not connected to voice error caught, try reconnecting
            if message.guild.voice_client is not None:
                await message.guild.voice_client.disconnect()
            if message.author.voice is not None:  # Check if the author is connected to a voice channel
                await message.author.voice.channel.connect()
                message.guild.voice_client.play(source)
            else:
                print("The author of the message is not connected to a voice channel.")
