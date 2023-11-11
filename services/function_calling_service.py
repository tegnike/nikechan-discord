# 使っていません

import json
import os
import io
import aiohttp
import discord
from dotenv import load_dotenv
from openai import OpenAI
from langchain.utilities import GoogleSearchAPIWrapper, SerpAPIWrapper
from services.attachment_service import encode_attachment

load_dotenv()
client = OpenAI()

async def search_web(tool_call):
    try:
        search_word = json.loads(tool_call.function.arguments)['search_word']

        url = 'https://preview.webpilotai.com/api/v1/watt'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {os.environ['WEBPILOT_API_KEY']}"
        }
        data = {
            "Content": f"「{search_word}」について調べ、日本語で回答してください。」"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                response_text = await response.text()
                print('WebPilotAPI search result:', json.loads(response_text)["content"])
                return response_text
    except Exception as e:
        print(f"WebPilotAPI Error: {e}")
        try:
            search = SerpAPIWrapper() #GoogleSearchAPIWrapper()
            result = await search.arun(search_word)
            print('SerpAPI search result:', result)
            return result
        except Exception as e2:
            print(f"SerpAPI Error: {e2}")
        return "情報を取得できませんでした。"

async def describe_image(tool_call, images):
    try:
        image_name = json.loads(tool_call.function.arguments)['image_name']
        user_question = json.loads(tool_call.function.arguments)['user_question']

        data = await encode_attachment(images[image_name])
        image_url = f"data:image/jpeg;base64, {data}"

        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{user_question}\nPlease answer in English."},
                        {
                            "type": "image_url",
                            "image_url": image_url,
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
        print("image_description:", response.choices[0].message.content)
        return response.choices[0].message.content
    except Exception as e:
        return "画像説明を生成できませんでした。"

async def create_image(message, tool_call):
    try:
        image_prompt = json.loads(tool_call.function.arguments)['image_prompt']

        response = client.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            n=1,
            size="1024x1024"
        )

        url = response.data[0].url
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.read()
        await message.channel.send(file=discord.File(fp=io.BytesIO(data), filename='image.png'))
        return "画像を生成が完了し、すでに別の方法でユーザーに共有済みです。"
    except Exception as e:
        return f"画像生成に失敗しました。"
