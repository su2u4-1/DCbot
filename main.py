from datetime import datetime
from dotenv import load_dotenv
from os import getenv

import discord
from discord.ext import commands

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.command()
async def start(ctx: commands.Context[commands.Bot]) -> None:
    await bot.tree.sync()
    await ctx.send("Bot started!")


@bot.command()
async def stop(ctx: commands.Context[commands.Bot]) -> None:
    await ctx.send("Bot stopped!")
    await bot.close()


@bot.command()
async def hello(ctx: commands.Context[commands.Bot]) -> None:
    """Say hello."""
    await ctx.send("Hello " + ctx.author.mention + "!")


@bot.hybrid_command()
async def time(ctx: commands.Context[commands.Bot]) -> None:
    """Get the current time."""
    await ctx.send(f"{datetime.now().strftime("%Y/%m/%d %H:%M:%S")}")


@bot.hybrid_command()
async def say(ctx: commands.Context[commands.Bot], message: str) -> None:
    """Echo the message."""
    await ctx.send(message)


token = getenv("TOKEN")
if token is None:
    print("Error: Missing Discord bot token")
else:
    bot.run(token)
