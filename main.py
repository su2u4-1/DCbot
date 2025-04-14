from dotenv import load_dotenv
import os

import discord
from discord.ext import commands

load_dotenv()

# intents = discord.Intents.default()
# intents.typing = False
# intents.presences = False
# intents.message_content = True

# client = discord.Client(intents=intents)


@client.event
async def on_ready() -> None:
    print(">>bot is online<<")


token = os.getenv("TOKEN")
if token is None:
    print("Error: Missing Discord bot token")
else:
    client.run(token)
