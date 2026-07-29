from datetime import datetime
from dotenv import load_dotenv
from os import getenv

import discord
from discord.ext import commands

import openai

load_dotenv()

client_ai = openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=getenv("KEY"))

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}", flush=True)
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} command(s)", flush=True)


@bot.event
async def on_message(message: discord.Message) -> None:
    if not isinstance(bot.user, discord.User):
        return
    if message.author == bot.user:
        return
    if bot.user in message.mentions:
        user_prompt = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()

        # 如果使用者只有 @ 機器人但沒有輸入任何文字
        if not user_prompt:
            await message.channel.send(f"你好 {message.author.mention}！有什麼我可以幫忙的嗎？")
            return

        # 觸發正在輸入中的提示(Typing Indicator)
        async with message.channel.typing():
            try:
                # 呼叫 OpenRouter API
                response = client_ai.chat.completions.create(
                    # 可選擇免費模型如 "openrouter/free" 或 "google/gemini-2.5-flash"
                    model="openrouter/free",
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一個很智障的 Discord AI 助手。",
                        },
                        {"role": "user", "content": user_prompt},
                    ],
                )

                # 取得 AI 回覆的文字
                ai_reply = response.choices[0].message.content

                # 回覆訊息並標記該使用者
                await message.reply(ai_reply)

            except Exception as e:
                print(f"OpenRouter API 呼叫失敗: {e}")
                await message.reply("抱歉，處理你的請求時發生錯誤，請稍後再試！")


# ============================


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


# ============================


@bot.hybrid_command()
async def hello(ctx: commands.Context[commands.Bot], user: discord.User | discord.Member | None = None) -> None:
    """Say hello."""
    print(f"> use hello by {ctx.author.mention}", flush=True)
    if user is None:
        user = ctx.author
    await ctx.send("Hello " + user.mention)


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
