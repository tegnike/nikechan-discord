from langchain.chat_models import ChatOpenAI
from langchain.schema import (
    SystemMessage,
    HumanMessage,
    AIMessage,
)

def get_system_message():
    with open('system_message.txt', 'r') as file:
        return file.read().strip()

def get_openai_response(message, history, model_name):
    # 過去10件のメッセージを取得
    latest_messages = history.messages[-10:]  
    past_messages = []
    for latest_message in latest_messages:
        if isinstance(latest_message, HumanMessage):
            past_messages.append(HumanMessage(content=latest_message.content))
        else:
            past_messages.append(AIMessage(content=latest_message.content))

    # 会話履歴を更新
    history.add_user_message(message)
    print("User:", message)

    # OpenAIによる応答生成
    messages = [SystemMessage(content=get_system_message())] + latest_messages + [HumanMessage(content=message)]
    chat = ChatOpenAI(model_name=model_name, temperature=0)
    response = chat(messages)

    # 会話履歴を更新
    history.add_ai_message(response.content)
    print("AI:", response.content)

    return response.content
