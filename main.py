import asyncio
from collections import OrderedDict, deque
from collections.abc import Sequence
from datetime import datetime
from dotenv import load_dotenv
from os import getenv

import discord
from discord.ext import commands

import openai
from openai.types.chat import ChatCompletionMessageParam

load_dotenv()

client_ai = openai.AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=getenv("KEY"))

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


def get_context_turns() -> int:
    value = getenv("CONTEXT_TURNS", "10")
    try:
        return max(0, int(value))
    except ValueError:
        return 10


def get_context_channel_limit() -> int:
    value = getenv("CONTEXT_CHANNEL_LIMIT", "1000")
    try:
        return max(1, int(value))
    except ValueError:
        return 1000


CONTEXT_TURNS = get_context_turns()
CONTEXT_CHANNEL_LIMIT = get_context_channel_limit()


class ChannelContext:
    __slots__ = ("history", "lock")

    def __init__(self) -> None:
        self.history: deque[ChatCompletionMessageParam] = deque(maxlen=max(1, CONTEXT_TURNS * 2))
        self.lock = asyncio.Lock()


conversation_contexts: OrderedDict[int, ChannelContext] = OrderedDict()


def prune_channel_contexts(protected_channel_id: int | None = None) -> None:
    while len(conversation_contexts) > CONTEXT_CHANNEL_LIMIT:
        for channel_id, context in conversation_contexts.items():
            if channel_id != protected_channel_id and not context.lock.locked():
                del conversation_contexts[channel_id]
                break
        else:
            return


def get_channel_context(channel_id: int) -> ChannelContext:
    context = conversation_contexts.get(channel_id)
    if context is None:
        context = ChannelContext()
        conversation_contexts[channel_id] = context
    else:
        conversation_contexts.move_to_end(channel_id)
    prune_channel_contexts(protected_channel_id=channel_id)
    return context


def build_chat_messages(history: Sequence[ChatCompletionMessageParam], user_prompt: str) -> list[ChatCompletionMessageParam]:
    recent_history = list(history[-CONTEXT_TURNS * 2 :]) if CONTEXT_TURNS else []
    return [
        {"role": "system", "content": getenv("PROMPT", "")},
        *recent_history,
        {"role": "user", "content": user_prompt},
    ]


def get_time() -> str:
    return datetime.now().strftime("%Y/%m/%d %H:%M:%S")


# @bot.event
# async def on_ready():
#     print(f"Logged in as {bot.user}", flush=True)
#     synced = await bot.tree.sync()
#     print(f"Synced {len(synced)} command(s)", flush=True)


@bot.event
async def on_message(message: discord.Message) -> None:
    if not isinstance(bot.user, discord.ClientUser):
        return
    if message.author == bot.user:
        return
    if bot.user in message.mentions:
        print(f"[{get_time()}] mention by {message.author.mention}: {message.content}", flush=True)
        user_prompt = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()

        if not user_prompt:
            await message.channel.send(f"你好 {message.author.mention}！有什麼我可以幫忙的嗎？")
            return

        context = get_channel_context(message.channel.id)
        try:
            async with context.lock:
                async with message.channel.typing():
                    try:
                        print(f"[{get_time()}] {message.author.mention}: {user_prompt}", flush=True)
                        response = await client_ai.chat.completions.create(
                            model="openrouter/free",
                            messages=build_chat_messages(context.history, user_prompt),
                        )

                        ai_reply = response.choices[0].message.content
                        if not ai_reply:
                            raise ValueError("OpenRouter returned an empty reply")
                        print(f"[{get_time()}] AI: {ai_reply}", flush=True)

                        await message.reply(ai_reply)
                        if CONTEXT_TURNS:
                            context.history.extend(
                                (
                                    {"role": "user", "content": user_prompt},
                                    {"role": "assistant", "content": ai_reply},
                                )
                            )

                    except openai.RateLimitError as e:
                        if e.status_code == 429:
                            print(f"OpenRouter API call rate limit error: {e}", flush=True)
                            await message.reply("⚠️ AI 目前今日免費額度已用完，請明天再試。")
                        else:
                            print(f"OpenRouter API call error: {e}", flush=True)
                            await message.reply("⚠️ 呼叫 AI 服務時發生錯誤，請稍後再試。")
                    except Exception as e:
                        print(f"OpenRouter API call error: {e}")
                        await message.reply("⚠️ 抱歉，處理你的請求時發生錯誤，請稍後再試。")
        finally:
            prune_channel_contexts()


# ============================


@bot.command()
@commands.is_owner()
async def start(ctx: commands.Context[commands.Bot]) -> None:
    print(f"[{get_time()}] use start by owner {ctx.author}", flush=True)
    synced = await bot.tree.sync()
    await ctx.send(f"Bot ready. Synced {len(synced)} command(s).")


@bot.command()
@commands.is_owner()
async def stop(ctx: commands.Context[commands.Bot]) -> None:
    print(f"[{get_time()}] use stop by owner {ctx.author.mention}", flush=True)
    await ctx.send("bot stopped")
    await bot.close()


# ============================


@bot.hybrid_command()
async def hello(ctx: commands.Context[commands.Bot], user: discord.User | discord.Member | None = None) -> None:
    """Say hello."""
    print(f"[{get_time()}] use hello by {ctx.author.mention}: {"None" if user is None else user.id}", flush=True)
    mention = ctx.author.mention if user is None else user.mention
    await ctx.send("Hello " + mention)


@bot.hybrid_command()
async def time(ctx: commands.Context[commands.Bot]) -> None:
    print(f"[{get_time()}] use time by {ctx.author.mention}", flush=True)
    """Get the current time."""
    await ctx.send(f"{get_time()}")


@bot.hybrid_command()
async def say(ctx: commands.Context[commands.Bot], message: str) -> None:
    print(f"[{get_time()}] use say by {ctx.author.mention}: {message}", flush=True)
    """Echo the message."""
    if "阿蘇" in message and "女裝" in message:
        await ctx.send(f"阿蘇不會女裝的，放棄吧\n-# <@{getenv("OWNER_ID")}> 有人亂講話")
    else:
        await ctx.send(message)


def main() -> None:
    token = getenv("TOKEN")
    if token is None:
        print("Error: Missing Discord bot token", flush=True)
        return
    print("bot start", flush=True)
    bot.run(token)
    print("bot stop", flush=True)


if __name__ == "__main__":
    main()
