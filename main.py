from datetime import datetime
from discord.ext import commands
from dotenv import load_dotenv
from openai.types.chat import ChatCompletionMessageParam
from os import getenv, makedirs
from os.path import exists, join, splitext
from typing import Optional
import aiohttp
import discord
import openai

load_dotenv()
client_ai = openai.AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=getenv("KEY"))
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_message(message: discord.Message) -> None:
    if not isinstance(bot.user, discord.ClientUser):
        return
    # 忽略所有 Bot 發送的訊息（包含自己）
    if message.author.bot:
        return

    # 判斷是否為「回覆 Bot 的訊息」
    is_reply_to_bot = False
    if message.reference and message.reference.message_id:
        try:
            ref_msg = await message.channel.fetch_message(message.reference.message_id)
            if ref_msg.author == bot.user:
                is_reply_to_bot = True
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

    # 觸發條件：被 Mention 或是 回覆 Bot 的訊息
    if bot.user in message.mentions or is_reply_to_bot:
        print(f"[{get_time()}] Triggered by {message.author}: {message.content}", flush=True)
        if message.guild and message.guild.me:
            bot_nick = message.guild.me.display_name
        else:
            bot_nick = bot.user.display_name if bot.user else "Bot"

        # 整理使用者輸入內容（去除 Mention 標籤）
        user_prompt = message.content.replace(f"<@{bot.user.id}>", f"@{bot_nick}").replace(f"<@!{bot.user.id}>", f"@{bot_nick}").strip()

        # 如果只有 Mention 但沒有輸入任何文字（且不是回覆鏈的一環）
        if not user_prompt and not message.reference:
            await message.reply(f"你好 {message.author.mention}！有什麼我可以幫忙的嗎？")
            return

        async with message.channel.typing():
            try:
                chain: list[discord.Message] = []
                curr: Optional[discord.Message] = message

                while curr:
                    chain.append(curr)
                    if curr.reference and curr.reference.message_id:
                        try:
                            curr = await curr.channel.fetch_message(curr.reference.message_id)
                        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                            curr = None
                    else:
                        curr = None

                chain.reverse()

                history: list[ChatCompletionMessageParam] = [{"role": "system", "content": str(getenv("PROMPT")) + f"你的暱稱是: `{bot_nick}`"}]
                for msg in chain:
                    clean_content = msg.content.replace(f"<@{message.guild.me.id if message.guild else ''}>", f"@{bot_nick}").strip()
                    if msg.author.bot:
                        history.append({"role": "assistant", "content": clean_content})
                    else:
                        history.append({"role": "user", "content": clean_content})

                response = await client_ai.chat.completions.create(model="openrouter/free", messages=history)
                ai_reply = response.choices[0].message.content
                if not ai_reply:
                    raise ValueError("OpenRouter returned an empty reply")

                print(f"[{get_time()}] AI: {ai_reply}", flush=True)

                await message.reply(ai_reply)

            except openai.RateLimitError as e:
                if e.status_code == 429:
                    print(f"OpenRouter API call rate limit error: {e}", flush=True)
                    await message.reply("⚠️ AI 目前今日免費額度已用完，請明天再試。")
                else:
                    print(f"OpenRouter API call error: {e}", flush=True)
                    await message.reply("⚠️ 呼叫 AI 服務時發生錯誤，請稍後再試。")
            except Exception as e:
                print(f"OpenRouter API call error: {e}", flush=True)
                await message.reply("⚠️ 抱歉，處理你的請求時發生錯誤，請稍後再試。")

    # 確保其他 bot 命令 (!command) 仍可正常運作
    await bot.process_commands(message)


# ============================


@bot.command()
async def start(ctx: commands.Context[commands.Bot]) -> None:
    if str(ctx.author.id) == getenv("OWNER_ID"):
        print(f"[{get_time()}] use start by owner {ctx.author}", flush=True)
        synced = await bot.tree.sync()
        await ctx.send(f"Bot ready. Synced {len(synced)} command(s).")


@bot.command()
async def stop(ctx: commands.Context[commands.Bot]) -> None:
    if str(ctx.author.id) == getenv("OWNER_ID"):
        print(f"[{get_time()}] use stop by owner {ctx.author}", flush=True)
        await ctx.send("bot stopped")
        await bot.close()


# ============================


def get_time() -> str:
    return datetime.now().strftime("%Y/%m/%d %H:%M:%S")


@bot.hybrid_command()
async def hello(ctx: commands.Context[commands.Bot], user: discord.User | discord.Member | None = None) -> None:
    """Say hello."""
    print(f"[{get_time()}] use hello by {ctx.author.mention}: {'None' if user is None else user.id}", flush=True)
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


@bot.hybrid_command()
async def archive_channel(ctx: commands.Context[commands.Bot]) -> None:
    folder_name = join("archive", str(ctx.channel.id))
    folder_path = join(__file__, folder_name)
    makedirs(folder_path, exist_ok=True)
    log_file_path = join(folder_path, "messages.txt")
    await ctx.send("開始讀取頻道歷史訊息並備份...")
    async with aiohttp.ClientSession() as session:
        with open(log_file_path, "w", encoding="utf-8") as f:
            f.write(f"channel: {ctx.guild.name if ctx.guild else "DM"}/{getattr(ctx.channel, "name", str(ctx.channel.id))} (ID: {ctx.channel.id})\n")
            async for msg in ctx.channel.history(limit=None, oldest_first=True):
                f.write(f"[{msg.created_at}] {msg.author} ({msg.author.id}): {msg.content}\n")
                for attachment in msg.attachments:
                    name, ext = splitext(attachment.filename)
                    index = 0
                    safe_filename = f"{name}_{index}{ext}"
                    while exists(join(folder_path, safe_filename)):
                        index += 1
                        safe_filename = f"{name}_{index}{ext}"
                    file_path = join(folder_path, safe_filename)
                    f.write(f" [appendix: {safe_filename} (url: {attachment.url})]\n")
                    try:
                        async with session.get(attachment.url) as resp:
                            if resp.status == 200:
                                data: bytes = await resp.read()
                                with open(file_path, "wb") as img_f:
                                    img_f.write(data)
                    except Exception as err:
                        print(f"下載附件失敗 {attachment.url}: {err}")
    await ctx.send(f"備份完成！資料已儲存至 `{folder_name}` 資料夾。")


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
