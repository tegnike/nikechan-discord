# 使っていません

from langchain.utilities import GoogleSearchAPIWrapper, SerpAPIWrapper
from dotenv import load_dotenv
import openai
import json, os, requests

load_dotenv()

def search_web(search_word):
    try: 
        url = 'https://preview.webpilotai.com/api/v1/watt'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {os.environ['WEBPILOT_API_KEY']}"
        }
        data = {
            "Content": f"「{search_word}」について調べ、日本語で回答してください。」"
        }

        response = requests.post(url, headers=headers, json=data)
        print('WebPilotAPI search result:', response.text)
        return response.text
    except Exception as e:
        print(f"Error: {e}")
        try:
            search = SerpAPIWrapper() #GoogleSearchAPIWrapper()
            result = search.run(search_word)
            print('SerpAPI search result:', result)
            return result
        except Exception as e2:
            print(f"Error: {e2}")
            return "情報を取得できませんでした。"

functions = [
    # 何をする関数かについて記述
    {
        "name": "search_web",
        "description": "インターネットから情報を検索する",
        "parameters": {
            "type": "object",
            "properties": {
                "search_word": {
                    "type": "string",
                    "description": "検索したい情報を入力。例: 東京 明日 天気",
                },
            },
            "required": ["search_word"],
        },
    }
]

async def ask_function_calling(history):
    print("function_calling start")
    MAX_REQUEST_COUNT = 5
    # ユーザーの入力をmessagesに格納
    messages = [{"role": "system", "content": "必要に応じ、与えられた情報を元に回答してください。情報を見つけられなかったという回答は許されません"}] + history

    for request_count in range(MAX_REQUEST_COUNT):
        print("request_count:", request_count)

        function_call_mode = "auto"
        if request_count == MAX_REQUEST_COUNT - 1:
            function_call_mode = "none"

        # ユーザーの入力内容から、Functions Callingが必要かどうか判断する
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages,
            functions=functions,
            function_call=function_call_mode,  # auto is default, but we'll be explicit
        )
        message = response["choices"][0]["message"]

        # Functions Callingが必要な場合は、additional_kwargsに関数名と引数を格納されている
        if message.get("function_call"):
            # messageから実行する関数と引数を取得
            function_name = message["function_call"]["name"]
            arguments = json.loads(message["function_call"]["arguments"])

            # 関数を実行
            function_response = search_web(
                search_word=(arguments.get("search_word")),
            )
            print("search word:", arguments.get("search_word"))
            print("search result:", function_response)

            # 実行結果をFunctionMessageとしてmessagesに追加
            messages.append({
                "role": "function",
                "name": function_name,
                "content": function_response,
            })

            if len(messages) > 15:
                messages.pop(0)
        else:
            if request_count == 0:
                return None
            else:
                return message["content"]
