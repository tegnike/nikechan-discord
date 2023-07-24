import discord

intents = discord.Intents.default()

class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged in as', self.user)

    async def on_message(self, message):
        # don't respond to ourselves
        if message.author == self.user:
            return

        if message.content == 'ping':
            await message.channel.send('pong')

client = MyClient(intents=intents)
client.run('MTEzMzE2MTU4MjQ1MzYwMDM3Nw.GtaoW-.5b5CtC0eXkKxSP2NPMgvy85EC7VeZUYUsmaxjk')
