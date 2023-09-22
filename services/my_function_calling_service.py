from services.system_message_service import get_system_message
from langchain.utilities import SerpAPIWrapper
from dotenv import load_dotenv
import openai
import json, os, aiohttp

load_dotenv()

async def search_web(search_word):
    try: 
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

async def check_if_i_dont_know(history):
    try:
        print("check_if_i_dont_know: start")

        last_assistant = next((item for item in reversed(history) if item['role'] == 'assistant'), None)
        last_user = next((item for item in reversed(history) if item['role'] == 'user'), None)
        prompt = get_system_message('judge_if_i_dont_know.txt').replace("{{USER_INPUT}}", last_user["content"]).replace("{{AI_INPUT}}", last_assistant["content"])
        response = openai.Completion.create(
            model="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=350,
            temperature=1.0,
        )
        response_content = response["choices"][0]["text"]
        print("check_if_i_dont_know: response:", response_content)
        response_json = json.loads(response_content.replace("\n", "").replace(" ", ""))
        print("check_if_i_dont_know: end")
        return response_json
    except Exception as e:
        print(f"check_if_i_dont_know: Error: {e}")
        raise Exception("check_if_i_dont_know: Error")

async def web_search_detail(first_result):
    print("web_search_detail: start")
    if not first_result["if_i_know"]:
        search_result = await search_web(first_result["search_word"])

        print("web_search_detail: end")
        return search_result
    # if not first_result["if_i_know"] and first_result["next_action"] != '':
    #     if first_result["next_action"] == "search_web":
    #         search_result = await search_web(first_result["additional_info"])

    #         print("web_search_detail: end")
    #         return search_result
    else:
        print("web_search_detail: end")
        raise Exception("invalid first_result")
