import os
import re
import json
import aiofiles
from typing import Dict, List, Any, Optional
from openai import OpenAI
from agents import Agent, Runner
from services.system_message_service import get_system_message, get_response_system_message
from services.attachment_service import get_attachment_data

client = OpenAI()

class SearchWebTool:
    """ウェブ検索を行うツール"""
    
    async def search_web(self, search_word: str) -> str:
        """
        指定されたキーワードでウェブ検索を行います。
        
        Args:
            search_word: 検索キーワード
            
        Returns:
            検索結果
        """
        try:
            import aiohttp
            
            url = "https://preview.webpilotai.com/api/v1/watt"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.environ['WEBPILOT_API_KEY']}",
            }
            data = {"Content": f"「{search_word}」について調べ、日本語で回答してください。」"}

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    response_text = await response.text()
                    print(
                        "WebPilotAPI search result:", json.loads(response_text)["content"]
                    )
                    return response_text
        except Exception as e:
            print(f"WebPilotAPI Error: {e}")
            try:
                from langchain.utilities import SerpAPIWrapper
                search = SerpAPIWrapper()
                result = await search.arun(search_word)
                print("SerpAPI search result:", result)
                return result
            except Exception as e2:
                print(f"SerpAPI Error: {e2}")
            return "情報を取得できませんでした。"


class DescribeImageTool:
    """画像説明を生成するツール"""
    
    async def describe_image(self, image_name: str, user_question: str, images: Dict[str, bytes]) -> str:
        """
        画像の説明を生成します。
        
        Args:
            image_name: 画像ファイル名
            user_question: ユーザーの質問
            images: 画像データの辞書
            
        Returns:
            画像の説明
        """
        try:
            from services.attachment_service import encode_attachment
            
            data = await encode_attachment(images[image_name])
            image_url = f"data:image/jpeg;base64, {data}"

            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"{user_question}\nPlease answer in English.",
                            },
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


class CreateImageTool:
    """画像生成を行うツール"""
    
    async def create_image(self, image_prompt: str, message) -> str:
        """
        指定されたプロンプトで画像を生成します。
        
        Args:
            image_prompt: 画像生成プロンプト
            message: Discordメッセージオブジェクト
            
        Returns:
            生成結果のメッセージ
        """
        try:
            import io
            import discord
            import aiohttp
            
            response = client.images.generate(
                model="dall-e-3", prompt=image_prompt, n=1, size="1024x1024"
            )

            url = response.data[0].url
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.read()
            await message.channel.send(
                file=discord.File(fp=io.BytesIO(data), filename="image.png")
            )
            return "画像を生成が完了し、すでに別の方法でユーザーに共有済みです。"
        except Exception as e:
            return f"画像生成に失敗しました。"


async def create_agent(system_message_type="base"):
    """
    エージェントを作成します。
    
    Args:
        system_message_type: システムメッセージのタイプ
        
    Returns:
        作成されたエージェント
    """
    system_message = get_response_system_message(system_message_type)
    
    agent = Agent(
        name="ニケ",
        instructions=system_message,
        tools=[
            SearchWebTool().search_web,
            DescribeImageTool().describe_image,
            CreateImageTool().create_image,
        ]
    )
    
    return agent


async def send_agent_response(message, messages_for_history, model_name, images=None):
    """
    エージェントを使用して応答を生成します。
    
    Args:
        message: Discordメッセージオブジェクト
        messages_for_history: 会話履歴
        model_name: 使用するモデル名
        images: 画像データの辞書（オプション）
        
    Returns:
        応答メッセージとエージェントの状態
    """
    agent = await create_agent()
    
    runner = Runner()
    
    content = ""
    for index, message_for_history in enumerate(messages_for_history):
        if index == len(messages_for_history) - 1:
            content = message_for_history
            if images and len(images) > 0:
                image_names = list(images.keys())
                content += f"\n次の画像が添付されています：{', '.join(image_names)}。\nこれらの画像から新しい画像を生成したい場合は、最初に describe_image 関数を使用し、その後で create_image 関数を使用してください。"
        else:
            content += message_for_history + "\n"
    
    try:
        result = await runner.run(agent, content, model=model_name)
        response_message = result.final_output
        
        await message.channel.send(response_message)
        
        return response_message, agent
    except Exception as e:
        print(f"Agent error: {e}")
        raise e


async def judge_if_i_response(message, history):
    """
    応答が必要かどうかを判断します。
    
    Args:
        message: Discordメッセージオブジェクト
        history: 会話履歴
        
    Returns:
        応答が必要かどうか
    """
    url_regex = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    if re.search(url_regex, message.content):  # URLチェック
        return False
    for attachment in message.attachments:  # ファイルサイズチェック
        if attachment.size > 512000000:
            return False
    if len(message.attachments) > 0:  # 添付チェック
        if message.content == "":
            return False
        else:
            return True
    if len(message.stickers) > 0:  # スタンプチェック
        return False
    if message.author.bot:  # botチェック
        return False

    latest_messages = history[-5:]
    past_messages = "You're name is 'ニケ'\n"
    for latest_message in latest_messages:
        if latest_message["role"] == "user":
            past_messages += (
                re.sub(
                    r"\(\d{4}/\d{2}/\d{2} \d{2}:\d{2}\)", "", latest_message["content"]
                )
                + "\n"
            )
        else:
            past_messages += "ニケ: " + latest_message["content"] + "\n"

    prompt = get_system_message("judge_if_i_response.txt").replace(
        "{{conversations}}", past_messages
    )
    response = client.completions.create(model="gpt-3.5-turbo-instruct", prompt=prompt)
    print("judge_if_i_response: response:", response.choices[0].text)
    result = response.choices[0].text.lower()
    return result.replace(" ", "") == "true"
