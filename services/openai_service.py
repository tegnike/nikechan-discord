from langchain.chat_models import ChatOpenAI
from langchain.schema import (
    SystemMessage,
    HumanMessage
)
from services.function_calling_service import ask_function_calling

def get_system_message(file_name):
    with open('services/system_messages/' + file_name, 'r') as file:
        return file.read().strip()

def get_openai_response(history, model_name, type=None):
    # 過去15件のメッセージを取得
    latest_messages = history.messages[-15:]
    print("latest_messages:", latest_messages)

    # functuion_calling
    function_calling_result = ask_function_calling(history.messages[-15:])
    if function_calling_result != None:
        print("function calling: True")
        print("function calling result:", function_calling_result)
        latest_messages.append(HumanMessage(content=("検索結果: " + function_calling_result)))
    else:
        print("function calling: False")

    # OpenAIによる応答生成
    messages = [SystemMessage(content=get_system_message("response_message.txt"))] + latest_messages
    llm = ChatOpenAI(model_name=model_name, temperature=0, max_tokens=350)
    response = llm(messages)
    response_message = response.content

    # 会話履歴を更新
    history.add_ai_message(response_message)
    print("AI:", response_message)

    if type != None:
        messages = [SystemMessage(content=get_system_message("message_convert_oji.txt"))] + [HumanMessage(content=("変換前文章：" + response_message))]
        llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
        response = llm(messages)
        return response.content
    else:
        return response_message

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
