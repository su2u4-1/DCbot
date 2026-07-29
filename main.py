from datetime import datetime
from dotenv import load_dotenv
from os import getenv

import discord
from discord.ext import commands

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}", flush=True)
    # 登入成功後自動同步一次斜線指令
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} command(s)", flush=True)


@bot.command()
@commands.is_owner()
async def start(ctx: commands.Context[commands.Bot]) -> None:
    print(f"> use start by owner {ctx.author}", flush=True)
    synced = await bot.tree.sync()
    await ctx.send(f"Bot ready. Synced {len(synced)} command(s).")


@bot.command()
@commands.is_owner()
async def stop(ctx: commands.Context[commands.Bot]) -> None:
    print(f"> use stop by owner {ctx.author.mention}", flush=True)
    await ctx.send("bot stopped")
    await bot.close()


@bot.command()
async def hello(ctx: commands.Context[commands.Bot]) -> None:
    print(f"> use hello by {ctx.author.mention}", flush=True)
    """Say hello."""
    await ctx.send("Hello " + ctx.author.mention)


@bot.hybrid_command()
async def time(ctx: commands.Context[commands.Bot]) -> None:
    print(f"> use time by {ctx.author.mention}", flush=True)
    """Get the current time."""
    await ctx.send(f"{datetime.now().strftime("%Y/%m/%d %H:%M:%S")}")


@bot.hybrid_command()
async def say(ctx: commands.Context[commands.Bot], message: str) -> None:
    print(f"> use say by {ctx.author.mention}", flush=True)
    """Echo the message."""
    if "阿蘇" in message and "女裝" in message:
        await ctx.send(f"阿蘇不會女裝的，放棄吧\n-# <@{getenv("OWNER_ID")}> 有人亂講話")
    else:
        await ctx.send(message)


token = getenv("TOKEN")
if token is None:
    print("Error: Missing Discord bot token", flush=True)
else:
    print("bot start", flush=True)
    bot.run(token)

print("bot stop", flush=True)
