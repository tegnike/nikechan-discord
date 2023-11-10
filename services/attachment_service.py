import os
import aiohttp
import base64

async def save_attachments(attachment):
    # 一時ファイルのパスを生成
    tmp_path = os.path.join('.tmp_files', attachment.filename)
    # aiohttpを使用してファイルを非同期でダウンロード
    async with aiohttp.ClientSession() as session:
        async with session.get(attachment.url) as resp:
            if resp.status == 200:
                # ファイルを書き込みモードで開き、ダウンロードしたコンテンツを書き込む
                with open(tmp_path, 'wb') as f:
                    while True:
                        chunk = await resp.content.read(1024)
                        if not chunk:
                            break
                        f.write(chunk)
            else:
                print(f"Failed to download {attachment.filename}")
    return attachment.filename

async def get_attachment_data(attachment):
    async with aiohttp.ClientSession() as session:
        async with session.get(attachment.url) as response:
            data = await response.read()

    return data

async def encode_attachment(data):
    encoded_data = base64.b64encode(data).decode('utf-8')

    return encoded_data
