# from datetime import datetime
# from pytz import timezone
# from langchain.memory import ChatMessageHistory
# from langchain.agents import load_tools
# from langchain.agents import initialize_agent
from langchain.chat_models import ChatOpenAI
# from langchain.chains.conversation.memory import ConversationBufferMemory
# from services.openai_service import get_openai_response, judge_if_i_response, get_join_response
# from services.voicevox_service import play_voice

# if __name__ == "__main__":
#     tools = load_tools(
#         tool_names = ["serpapi", "llm-math"],
#         llm = ChatOpenAI(temperature=0)
#     )
#     memory = ConversationBufferMemory(
#         memory_key = "chat_history",
#         return_messages = True,
#     )
#     agent = initialize_agent(
#         agent = "zero-shot-react-description",
#         llm = ChatOpenAI(temperature=0),
#         tools = tools,
#         memory = memory,
#         verbose = True,
#     )

#     while True:
#         # コンソールからテキストを受け取る。
#         console_text = input("Please enter your text (or 'q' to quit): ")
    
#         # ユーザーが 'q' を入力したらループを終了する。
#         if console_text.lower() == 'q':
#             break

#         # 受け取ったテキストを引数にして exec 関数を実行する。
#         agent.run(console_text)

# パッケージのインポート
import os

# from llama_index import GPTVectorStoreIndex, SimpleDirectoryReader

import langchain
from langchain import OpenAI, SerpAPIWrapper
from langchain.agents import Tool, initialize_agent
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from langchain.schema import (
    SystemMessage,
    HumanMessage,
    AIMessage,
)
os.environ["OPENAI_API_KEY"] = "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"
langchain.verbose = True

# documents = SimpleDirectoryReader("data").load_data()
# index = GPTVectorStoreIndex.from_documents(documents)



def get_system_message(file_name):
    with open('services/system_messages/' + file_name, 'r') as file:
        return file.read().strip()

if __name__ == "__main__":
    search = SerpAPIWrapper(serpapi_api_key="718f40d17b94a1533c4920716708fd5bc8fe0b1c7a4ea9a85d829be43eb3a116")
    tools = [
        # Tool(
        #     name="Kanmon Tunnel",
        #     func=lambda q: str(index.as_query_engine().query(q)),
        #     description="Useful for the generating the answers of Kanmon Tunnel",
        #     return_direct=True,
        # ),
        Tool(
            name="Search",
            func=search.run,
            description="useful for when you need to answer questions about current events",
        ),
    ]

    messages = [SystemMessage(content=get_system_message("response_message.txt"))]
    chat = ChatOpenAI(model_name=model_name, temperature=0, max_tokens=350)

    agent = initialize_agent(
        tools = tools,
        llm=ChatOpenAI(temperature=0),
        gent="zero-shot-react-description",
        verbose=True,
    )

    while True:
        # コンソールからテキストを受け取る。
        console_text = input("Please enter your text (or 'q' to quit): ")
    
        # ユーザーが 'q' を入力したらループを終了する。
        if console_text.lower() == 'q':
            break

        # 受け取ったテキストを引数にして exec 関数を実行する。
        agent.run(console_text)