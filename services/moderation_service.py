import os, json, random
from openai import OpenAI


async def check_moderation(message):
    client = OpenAI()

    response = client.moderations.create(input=message.content)

    if response.results[0].flagged:
        with open("services/scripts/moderation_messages", "r") as f:
            moderation_messages = json.load(f)

            await message.channel.send(random.choice(moderation_messages))

            return True
    else:
        return False
