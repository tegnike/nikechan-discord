from langchain.chat_models import ChatOpenAI
from langchain.schema import (
    SystemMessage,
    HumanMessage,
    AIMessage,
)

def get_system_message():
    with open('system_message.txt', 'r') as file:
        return file.read().strip()

def get_system_message2():
    with open('system_message2.txt', 'r') as file:
        return file.read().strip()

def get_openai_response(history, model_name):
    # 過去15件のメッセージを取得
    latest_messages = history.messages[-15:]

    # OpenAIによる応答生成
    print("latest_messages:", latest_messages)
    messages = [SystemMessage(content=get_system_message())] + latest_messages
    chat = ChatOpenAI(model_name=model_name, temperature=0, max_tokens=350)
    response = chat(messages)

    # 会話履歴を更新
    history.add_ai_message(response.content)
    print("AI:", response.content)

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
    messages = [SystemMessage(content=get_system_message2())] + [HumanMessage(content=past_messages)]
    chat = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=1.0, max_tokens=2)
    response = chat(messages)

    result = response.content.lower()
    return result == "true"
