import random
import discord
import os
import pytz
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ['DISCORD_KEY']
CHANNEL_ID = 1090678631489077331
API_KEY = os.environ['GOOGLE_API_KEY']
CHANNEL_IDS = {'スイちゃん': 'UCl5shU0C8jjo81SB-V4jEtA', 'ここママ': 'UCkICVOSNH4AXjJnQ6dNeehA'}

intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)

TEXT_LIST = [
  "CHARACTER_NAMEの新しいYouTube動画がアップされました❣見逃さないでね❣",
  "CHARACTER_NAMEの新しいYouTube動画が公開されました！今回も見応えたっぷりだから、すぐにでもチェックしてください！",
  "CHARACTER_NAMEのYouTubeチャンネルに新しい動画が登場しました。一緒に楽しみましょう！",
  "速報です！CHARACTER_NAMEから新しい動画のプレゼントが！今すぐYouTubeでチェックしてみてください！",
  "🌟お知らせ🌟 CHARACTER_NAMEの最新YouTube動画が公開されました！今回の内容は必見です！みんな、急いでチェックしてね！",
  "📢速報！ CHARACTER_NAMEより素敵な新動画がYouTubeに届けられました！一緒に視聴しましょう！",
  "🎉新作動画アラート🎉 CHARACTER_NAMEのYouTubeチャンネルに新しい動画がアップされました！リンクをクリックして、魅力的な世界へ飛び込みましょう！",
  "みなさん、待望のニュースですよ！CHARACTER_NAMEのYouTubeチャンネルに新動画がアップされました。今回のテーマはとっても興味深いですよ！",
  "🚀更新タイム🚀 CHARACTER_NAMEのYouTubeチャンネルで新しい動画の波が到来！この機会を見逃さないように！",
  "新作動画のお時間です！CHARACTER_NAMEがYouTubeに最新作を投稿されたようです！今すぐ視聴リストに追加追加！",
  "🌈驚きのニュース🌈 CHARACTER_NAMEのクリエイティビティが溢れる最新YouTube動画を見て、今日一日を特別なものにしましょう！",
  "注目！CHARACTER_NAMEがYouTubeに新しい動画をアップロードされたようです。コンテンツを楽しみたいなら、今がその時！",
  "🌟特報！🌟 CHARACTER_NAMEのYouTubeチャンネルが更新されたようです。今回の動画は見る価値あり！すぐにチェックしてみてください。",
  "皆さん、聞いてください！CHARACTER_NAMEの最新の投稿がYouTubeで公開されました！私も早速チェックしてみますね！",
  "速報！CHARACTER_NAMEの新しい動画がアップロードされました！私もウキウキしてます！早速見ましょうね！",
  "お知らせです！CHARACTER_NAMEの新たな動画がYouTubeでお目見えしました！今すぐチェックしてみてくださいね！",
  "皆さん待望の新作動画がCHARACTER_NAMEから登場！さあ、一緒に楽しみましょう！",
  "CHARACTER_NAMEの新動画が公開されました！今すぐ見て、新たな発見を楽しみましょう！",
  "速報！CHARACTER_NAMEの最新のYouTube動画が公開されました！見逃さないでくださいね！",
  "新着情報！CHARACTER_NAMEの新しいYouTube動画が私たちを待っています！一緒に視聴しませんか？",
  "CHARACTER_NAMEの新しい動画が公開されましたよ！私も今から見ることがとても楽しみです！",
  "速報です！CHARACTER_NAMEの新しいYouTube動画が公開されました！一緒に視聴しましょう！",
  "お知らせです！CHARACTER_NAMEの新たな動画がYouTubeでお目見えしました！今すぐチェックしてみてくださいね！",
]

def get_latest_videos():
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    now = datetime.now(pytz.UTC)
    # 分を10分単位で切り捨てるために、現在の分に対して10で割ってから切り捨て、再び10を掛ける
    truncated_minutes = (now.minute // 10) * 10
    # 切り捨てた分を設定し、さらに11分前を求める
    start_time = now.replace(minute=truncated_minutes, second=0, microsecond=0) - timedelta(minutes=11)
    # start_time = now - timedelta(hours=10)
    messages = []

    for channel_name, channel_id in CHANNEL_IDS.items():
        response = youtube.search().list(
            part='snippet',
            channelId=channel_id,
            maxResults=5,
            order='date',
            type='video',
            publishedAfter=start_time.isoformat()
        ).execute()

        for item in response.get('items', []):
            video_id = item['id']['videoId']

            # call_youtube.txtから動画IDを取得し、重複している場合はスキップ
            # 重複していない場合は、動画IDをcall_youtube.txtに追加
            with open('call_youtube.txt', 'r') as f:
                video_ids = f.read().splitlines()
                if video_id in video_ids:
                    continue
                video_ids.append(video_id)
            with open('call_youtube.txt', 'w') as f:
                f.write('\n'.join(video_ids))

            title = item['snippet']['title']
            # published_at = item['snippet']['publishedAt']
            video_url = f'https://www.youtube.com/watch?v={video_id}'
            # TEXT_LISTからランダムにメッセージを取得
            message = random.choice(TEXT_LIST).replace('CHARACTER_NAME', channel_name)
            message = f'{message}\n『{title}』\n{video_url}'
            messages.append(message)

    return messages

async def send_messages():
    channel = client.get_channel(CHANNEL_ID)
    print(channel)
    if channel:
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
