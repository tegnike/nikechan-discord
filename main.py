import discord

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

class MyClient(discord.Client):
    async def on_ready(self):
        print('Bot is ready.')
        print('Logged in as', self.user)

    async def on_message(self, message):
        print('Message received from', message.author, ':', message.content)
        
        # don't respond to ourselves
        if message.author == self.user:
            print('Message received from self, ignoring.')
            return

        if message.content == 'ping':
            print('Ping received, sending pong.')
            await message.channel.send('pong')
        else:
            print('Message not recognized.')

client = MyClient(intents=intents)
client.run('MTEzMzE2MTU4MjQ1MzYwMDM3Nw.GiWxQf.g4cnVupSdVI5YmZBmqlDkkpMmKmJqjXjYVuIzA')
