from datetime import datetime
from openai import OpenAI


class MongoAdapter:
    def __init__(self, collection_states, collection_chats):
        self.collection_states = collection_states
        self.collection_chats = collection_chats
        self.client = OpenAI()

    def get_or_create_state(self, server_id):
        state = self.collection_states.find_one({"server_id": server_id})
        if state is None:
            thread = self.client.beta.threads.create()
            state = {
                "server_id": server_id,
                "messages_for_history": [],
                "messages_for_judge": [],
                "count": 0,
                "current_date": datetime.now(timezone("Europe/Warsaw")).date(),
                "is_daily_limit": False,
                "is_monthly_limit": False,
                "thread_id": thread.id,
            }
            self._to_mongo(state)
            self.collection_states.insert_one(state)
        self._from_mongo(state)
        return state

    def update_state(self, server_id, state):
        self._to_mongo(state)
        self.collection_states.update_one({"server_id": server_id}, {"$set": state})

    def save_chat(self, server_id, message_content, response):
        self.collection_chats.insert_one(
            {"server_id": server_id, "user": message_content, "assistant": response}
        )

    def _to_mongo(self, state):
        state["current_date"] = state["current_date"].strftime("%Y-%m-%d")

    def _from_mongo(self, state):
        state["current_date"] = datetime.strptime(
            state["current_date"], "%Y-%m-%d"
        ).date()
