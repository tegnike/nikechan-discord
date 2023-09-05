import openai
import os, json, random

openai.api_key = os.environ['OPENAI_API_KEY']

async def check_moderation(message):
    response = openai.Moderation.create(
        input = message.content
    )

    if response.results[0].flagged:
        with open('services/scripts/moderation_messages', 'r') as f:
            moderation_messages = json.load(f)

            await message.channel.send(random.choice(moderation_messages))

            return True
    else:
        return False
