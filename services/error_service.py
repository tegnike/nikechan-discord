import os
from services.select_random_message_service import select_random_message

error_send_channel = 1090678631489077331
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

async def send_error_message(client, message, error_message):
    if error_message == 'You exceeded your current quota, please check your plan and billing details.':
        print('API制限に達しました。')
        await message.channel.send(select_random_message('error_messages'))
    else:
        # メッセージリストからランダムに選択
        await message.channel.send(select_random_message('error_messages'))
    print("Error:", error_message)

    for key, value in allowed_channels.items():
         if message.channel.id == value:
            target_channel = client.get_channel(int(error_send_channel))
            await target_channel.send(f"<@576031815945420812>\n{key}サーバーでエラーが発生しました。\n============================================\n{error_message}\n============================================")
