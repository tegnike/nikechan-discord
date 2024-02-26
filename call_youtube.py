# task.py
import discord
import os
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ['DISCORD_KEY']
CHANNEL_ID = 1090678631489077331
API_KEY = os.environ['GOOGLE_API_KEY']
CHANNEL_IDS = ['UCl5shU0C8jjo81SB-V4jEtA', 'UCkICVOSNH4AXjJnQ6dNeehA']

intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)

def get_latest_videos():
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    now = datetime.now(pytz.UTC)
    one_hour_ago = now - timedelta(hours=1)
    messages = []

    for channel_id in CHANNEL_IDS:
        response = youtube.search().list(
            part='snippet',
            channelId=channel_id,
            maxResults=5,
            order='date',
            type='video',
            publishedAfter=one_hour_ago.isoformat()
        ).execute()

        for item in response.get('items', []):
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            published_at = item['snippet']['publishedAt']
            video_url = f'https://www.youtube.com/watch?v={video_id}'
            messages.append(f'Title: {title}, Published At: {published_at}, URL: {video_url}')

    return messages

async def send_messages():
    channel = client.get_channel(CHANNEL_ID)
    print('Sending messages...')
    print(channel)
    if channel:
        print('Sending messages...')
        messages = get_latest_videos()
        for message in messages:
            print(message)
            await channel.send(message)
    await client.close()

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    client.loop.create_task(send_messages())

client.run(TOKEN)
