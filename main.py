from datetime import datetime
from os import getenv, makedirs
from os.path import dirname, exists, join, splitext

import aiofiles
import aiohttp
import asyncio
import discord
import openai
from discord.ext import commands
from dotenv import load_dotenv
from openai.types.chat import ChatCompletionMessageParam

load_dotenv()
client_ai = openai.AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=getenv("KEY"))
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# ============================


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
                curr: discord.Message | None = message

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
    """Get the current time."""
    print(f"[{get_time()}] use time by {ctx.author.mention}", flush=True)
    await ctx.send(f"{get_time()}")


@bot.hybrid_command()
async def say(ctx: commands.Context[commands.Bot], message: str) -> None:
    """Echo the message."""
    print(f"[{get_time()}] use say by {ctx.author.mention}: {message}", flush=True)
    if "阿蘇" in message and "女裝" in message:
        await ctx.send(f"阿蘇不會女裝的，放棄吧\n-# <@{getenv("OWNER_ID")}> 有人亂講話")
    else:
        await ctx.send(message)


# ============================


@bot.hybrid_command()
async def archive_channel(ctx: commands.Context[commands.Bot]) -> None:
    """Archive the current channel's message history and attachments."""
    print(f"[{get_time()}] use archive_channel by {ctx.author.mention}", flush=True)
    # 1. 延遲回應：處理大規模資料時間較長，避免 Discord 指令 3 秒逾時失敗
    await ctx.defer()

    folder_name = join("archive", str(ctx.channel.id))
    if exists(folder_name):
        folder_name += datetime.now().strftime("_%Y-%m-%d-%H-%M-%S")
    folder_path = join(dirname(__file__), folder_name)
    makedirs(folder_path, exist_ok=True)
    log_file_path = join(folder_path, "messages.txt")

    await ctx.send("開始讀取頻道歷史訊息並備份（大規模備份中...）")

    # 限制同時下載圖片的數量（避免封包堵塞或被 CDN 限流）
    semaphore = asyncio.Semaphore(10)

    # 建立生產者-消費者佇列 (Queue)，避免一次把上萬個 Task 排入 Event Loop 導致記憶體暴增
    download_queue: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()

    # 輔助函式：帶有 HTTP 429 / 5xx 重試機制的非同步串流下載器
    async def download_worker() -> None:
        async with aiohttp.ClientSession() as session:
            while True:
                item = await download_queue.get()
                if item is None:  # 收到結束信號 (Poison Pill)
                    download_queue.task_done()
                    break

                url, target_path = item
                async with semaphore:
                    max_retries = 5
                    for attempt in range(max_retries):
                        try:
                            async with session.get(url) as resp:
                                # 處理 CDN Rate Limit (HTTP 429)
                                if resp.status == 429:
                                    retry_after = float(resp.headers.get("Retry-After", 2.0))
                                    await asyncio.sleep(retry_after)
                                    continue

                                # 處理伺服器端暫時性錯誤 (HTTP 5xx) -> 指數退避
                                if resp.status >= 500:
                                    await asyncio.sleep(2**attempt)
                                    continue

                                if resp.status == 200:
                                    async with aiofiles.open(target_path, "wb") as img_f:
                                        async for chunk in resp.content.iter_chunked(1024 * 1024):  # 1MB
                                            await img_f.write(chunk)
                                    break  # 下載成功，跳出重試迴圈
                        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                            if attempt == max_retries - 1:
                                print(f"下載附件失敗 {url}: {err}")
                            await asyncio.sleep(2**attempt)

                download_queue.task_done()

    # 啟動 10 個背景 Worker 工作線程
    worker_count = 10
    workers = [asyncio.create_task(download_worker()) for _ in range(worker_count)]

    # 追蹤已產生的檔名，改用記憶體內 Set 進行 O(1) 檔名碰撞檢測，保護硬碟 I/O
    used_filenames: set[str] = set()

    # 使用 aiofiles 非同步寫入文字紀錄檔
    async with aiofiles.open(log_file_path, "w", encoding="utf-8-sig") as f:
        guild_name = ctx.guild.name if ctx.guild else "DM"
        channel_name = getattr(ctx.channel, "name", str(ctx.channel.id))
        await f.write(f"channel: {guild_name}/{channel_name}, id: {ctx.channel.id}, time: {get_time()}\n")

        # 2. 批次讀取歷史訊息
        async for msg in ctx.channel.history(limit=None, oldest_first=True):
            await f.write(f"[{msg.created_at}] {msg.author} ({msg.author.id}): {msg.content}\n")

            for attachment in msg.attachments:
                name, ext = splitext(attachment.filename)
                index = 0
                safe_filename = f"{name}_{index}{ext}"

                # 優先檢查記憶體內的 Set，若無才檢查實體硬碟，大幅減少硬碟磁碟 I/O 次數
                while safe_filename in used_filenames or exists(join(folder_path, safe_filename)):
                    index += 1
                    safe_filename = f"{name}_{index}{ext}"

                used_filenames.add(safe_filename)
                file_path = join(folder_path, safe_filename)
                await f.write(f" [appendix: {safe_filename} (url: {attachment.url})]\n")

                # 將下載任務放入佇列，讓背景 Worker 處理
                await download_queue.put((attachment.url, file_path))

    # 等待佇列中的所有圖片下載任務完成
    await download_queue.join()

    # 發送 Poison Pill 關閉所有背景 Worker
    for _ in range(worker_count):
        await download_queue.put(None)
    await asyncio.gather(*workers)

    # 傳送完成訊息
    await ctx.send(f"備份完成！資料已儲存至 `{folder_name}` 資料夾。")


# ============================


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
