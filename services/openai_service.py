from langchain.chat_models import ChatOpenAI
from langchain.schema import (
    SystemMessage,
    HumanMessage,
    FunctionMessage
)
import json
import os
from serpapi import GoogleSearch

def search_web(search_word):
    api_key = os.getenv('SERPAPI_API_KEY')
    
    search = GoogleSearch({
        "q": search_word,
        "api_key": api_key
    })
    
    results = search.get_json()
    result = process_response(results)

    return result

def process_response(res: dict) -> str:
    """Process response from SerpAPI."""
    if "error" in res.keys():
        raise ValueError(f"Got error from SerpAPI: {res['error']}")
    if "answer_box" in res.keys() and type(res["answer_box"]) == list:
        res["answer_box"] = res["answer_box"][0]
    if "answer_box" in res.keys() and "answer" in res["answer_box"].keys():
        toret = res["answer_box"]["answer"]
    elif "answer_box" in res.keys() and "snippet" in res["answer_box"].keys():
        toret = res["answer_box"]["snippet"]
    elif (
        "answer_box" in res.keys()
        and "snippet_highlighted_words" in res["answer_box"].keys()
    ):
        toret = res["answer_box"]["snippet_highlighted_words"][0]
    elif (
        "sports_results" in res.keys()
        and "game_spotlight" in res["sports_results"].keys()
    ):
        toret = res["sports_results"]["game_spotlight"]
    elif (
        "shopping_results" in res.keys()
        and "title" in res["shopping_results"][0].keys()
    ):
        toret = res["shopping_results"][:3]
    elif (
        "knowledge_graph" in res.keys()
        and "description" in res["knowledge_graph"].keys()
    ):
        toret = res["knowledge_graph"]["description"]
    elif "snippet" in res["organic_results"][0].keys():
        toret = res["organic_results"][0]["snippet"]
    elif "link" in res["organic_results"][0].keys():
        toret = res["organic_results"][0]["link"]
    elif (
        "images_results" in res.keys()
        and "thumbnail" in res["images_results"][0].keys()
    ):
        thumbnails = [item["thumbnail"] for item in res["images_results"][:10]]
        toret = thumbnails
    else:
        toret = "No good search result found"
    return toret


def get_system_message(file_name):
    with open('services/system_messages/' + file_name, 'r') as file:
        return file.read().strip()

def get_openai_response(history, model_name, type=None):
    # AIが利用する関数の定義
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
    
    # 過去15件のメッセージを取得
    latest_messages = history.messages[-15:]

    # OpenAIによる応答生成
    print("latest_messages:", latest_messages)
    messages = [SystemMessage(content=get_system_message("response_message.txt"))] + latest_messages
    llm = ChatOpenAI(model_name=model_name, temperature=0, max_tokens=350)
    response = llm.predict_messages(messages, functions=functions)

    # 会話履歴を更新
    history.add_ai_message(response.content)

    if response.additional_kwargs:
        # function_call = response["choices"][0]["message"].get("function_call")
        # function_name = function_call.get("name")

        # if function_name in [f["name"] for f in functions]:
        #     function_arguments = function_call.get("arguments")
        #     function_response = eval(function_name)(**eval(function_arguments))
        # else:
        #     raise Exception
    
        # messageから実行する関数と引数を取得
        function_name = response.additional_kwargs["function_call"]["name"]
        arguments = json.loads(response.additional_kwargs["function_call"]["arguments"])

        # 関数を実行
        function_response = search_web(
            search_word=arguments.get("search_word"),
        )
        print("function_response:", function_response)

        # 実行結果をFunctionMessageとしてmessagesに追加
        function_message = FunctionMessage(name=function_name, content=function_response)
        messages.append(function_message)

        print("messages with Function Calling:", messages)
        # FuncitonMessageを元に、AIの回答を取得
        second_response = llm.predict_messages(
            messages=messages, functions=functions
        )
        print("AI with Function Calling:", second_response.content)
        if type != None:
            messages = [SystemMessage(content=get_system_message("message_convert_oji.txt"))] + [HumanMessage(content=("変換前文章：" + second_response.content))]
            chat = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
            second_response = chat(messages)
            return second_response.content
        else:
            return second_response.content
    else:
        print("AI:", response.content)
        if type != None:
            messages = [SystemMessage(content=get_system_message("message_convert_oji.txt"))] + [HumanMessage(content=("変換前文章：" + response.content))]
            chat = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
            response = chat(messages)
            return response.content
        else:
            return response.content

def judge_if_i_response(history):
    # 過去5件のメッセージを取得
    latest_messages = history.messages[-5:]
    past_messages = "You're name is 'ニケ'\n"
    for latest_message in latest_messages:
        if isinstance(latest_message, HumanMessage):
            past_messages += latest_message.content + "\n"
        else:
            past_messages += "ニケ: " + latest_message.content + "\n"

    # OpenAIによる応答生成
    messages = [SystemMessage(content=get_system_message("judge_if_i_response.txt"))] + [HumanMessage(content=past_messages)]
    chat = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=1.0, max_tokens=2)
    response = chat(messages)

    result = response.content.lower()
    return result == "true"

def get_join_response(user_name):
    # OpenAIによる応答生成
    messages = [SystemMessage(content=get_system_message("join_message.txt"))] + [HumanMessage(content=user_name)]
    chat = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0, max_tokens=150)
    response = chat(messages)

    print("AI join message:", response.content)

    return response.content
