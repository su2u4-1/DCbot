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
    print("> use start")
    await bot.tree.sync()
    await ctx.send("Bot started!")


@bot.command()
async def stop(ctx: commands.Context[commands.Bot]) -> None:
    print("> use stop")
    if str(ctx.author.id) == getenv("OWNER_ID"):
        await ctx.send("Bot stopped!")
        await bot.close()
    else:
        await ctx.send("You are not authorized to stop the bot.")


@bot.command()
async def hello(ctx: commands.Context[commands.Bot]) -> None:
    print("> use hello")
    """Say hello."""
    await ctx.send("Hello " + ctx.author.mention + "!")


@bot.hybrid_command()
async def time(ctx: commands.Context[commands.Bot]) -> None:
    print("> use time")
    """Get the current time."""
    await ctx.send(f"{datetime.now().strftime("%Y/%m/%d %H:%M:%S")}")


@bot.hybrid_command()
async def say(ctx: commands.Context[commands.Bot], message: str) -> None:
    print("> use say")
    """Echo the message."""
    if "阿蘇" in message and "女裝" in message:
        await ctx.send(f"阿蘇不會女裝的，放棄吧\n-# <@{getenv("OWNER_ID")}> 有人亂講話")
    else:
        await ctx.send(message)


token = getenv("TOKEN")
if token is None:
    print("Error: Missing Discord bot token")
else:
    print("bot start")
    bot.run(token)

print("bot stop")
