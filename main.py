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

                if "女裝" in ai_reply:
                    ai_reply = "⚠️ 禁止女裝！"

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
    if "女" in message and "裝" in message:
        await ctx.send(f"禁止女裝！")
    else:
        await ctx.send(message)


# ============================


@bot.hybrid_command()
async def archive_channel(ctx: commands.Context[commands.Bot]) -> None:
    """Archive the current channel's message history and attachments."""
    print(f"[{get_time()}] use archive_channel by {ctx.author.mention}", flush=True)
    await ctx.defer()

    folder_name = join("archive", str(ctx.channel.id))
    if exists(folder_name):
        folder_name += datetime.now().strftime("_%Y-%m-%d-%H-%M-%S")
    folder_path = join(dirname(__file__), folder_name)
    makedirs(folder_path, exist_ok=True)
    log_file_path = join(folder_path, "messages.txt")

    await ctx.send("開始讀取頻道歷史訊息並備份（大規模備份中...）")

    semaphore = asyncio.Semaphore(10)
    download_queue: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()
    file_set: dict[str, str] = {}  # 用於追蹤已下載的檔案，避免重複下載

    async def download_worker() -> None:
        async with aiohttp.ClientSession() as session:
            while True:
                item = await download_queue.get()
                if item is None:  # Poison Pill
                    download_queue.task_done()
                    break

                url, target_path = item
                async with semaphore:
                    max_retries = 5
                    for attempt in range(max_retries):
                        try:
                            async with session.get(url) as resp:
                                if resp.status == 429:
                                    retry_after = float(resp.headers.get("Retry-After", 2.0))
                                    await asyncio.sleep(retry_after)
                                    continue

                                if resp.status >= 500:
                                    await asyncio.sleep(2**attempt)
                                    continue

                                if resp.status == 200:
                                    async with aiofiles.open(target_path, "wb") as img_f:
                                        async for chunk in resp.content.iter_chunked(1024 * 1024):
                                            await img_f.write(chunk)
                                    break
                        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                            if attempt == max_retries - 1:
                                print(f"下載附件失敗 {url}: {err}")
                            await asyncio.sleep(2**attempt)

                download_queue.task_done()

    worker_count = 10
    workers = [asyncio.create_task(download_worker()) for _ in range(worker_count)]
    used_filenames: set[str] = set()

    # 輔助函式：產生唯一且安全的檔名
    def get_safe_filename(original_filename: str) -> str:
        name, ext = splitext(original_filename)
        # 若貼圖副檔名缺失，設預設副檔名
        if not ext:
            ext = ".png"
        index = 0
        safe_filename = f"{name}_{index}{ext}"
        while safe_filename in used_filenames or exists(join(folder_path, safe_filename)):
            index += 1
            safe_filename = f"{name}_{index}{ext}"
        used_filenames.add(safe_filename)
        return safe_filename

    # 輔助函式：格式化處理訊息（支援普通訊息與轉發訊息內容）
    async def process_attachments_and_stickers(attachments: list[discord.Attachment], stickers: list[discord.StickerItem], indent: str = "    ") -> None:
        # 1. 處理一般的附件 (Attachments)
        for attachment in attachments:
            safe_filename = get_safe_filename(attachment.filename)
            file_path = join(folder_path, safe_filename)
            if attachment.url not in file_set:
                await f.write(f"{indent}[appendix: {safe_filename} (url: {attachment.url})]\n")
                await download_queue.put((attachment.url, file_path))
            else:
                await f.write(f"{indent}[appendix: {file_set[file_path]} (url: {attachment.url})]\n")

        # 2. 處理貼圖 (Stickers)
        for sticker in stickers:
            # 貼圖檔名加上 sticker_ 首綴以利辨別，若無 filename 屬性則拿貼圖名稱或 ID
            raw_filename = f"sticker_{sticker.name}"
            safe_filename = get_safe_filename(raw_filename)
            file_path = join(folder_path, safe_filename)
            if sticker.url not in file_set:
                await f.write(f"{indent}[appendix: {safe_filename} (url: {sticker.url})]\n")
                await download_queue.put((sticker.url, file_path))
            else:
                await f.write(f"{indent}[appendix: {file_set[file_path]} (url: {sticker.url})]\n")

    async with aiofiles.open(log_file_path, "w", encoding="utf-8-sig") as f:
        guild_name = ctx.guild.name if ctx.guild else "DM"
        channel_name = getattr(ctx.channel, "name", str(ctx.channel.id))
        await f.write(f"channel: {guild_name}/{channel_name}, id: {ctx.channel.id}, time: {get_time()}\n")

        async for msg in ctx.channel.history(limit=None, oldest_first=True):
            # 主訊息輸出
            await f.write(f"[{msg.created_at}] {msg.author} ({msg.author.id}): {msg.content}\n")

            # 處理主訊息的附件與貼圖
            await process_attachments_and_stickers(msg.attachments, msg.stickers, indent=" ^ ")

            # 3. 處理轉發訊息 (Message Snapshots)
            if hasattr(msg, "message_snapshots") and msg.message_snapshots:
                for snapshot in msg.message_snapshots:
                    snap_content = snapshot.content
                    snap_attachments = snapshot.attachments

                    # 判斷是否包含文字內容
                    has_content = bool(snap_content and snap_content.strip())

                    await f.write(f"[{msg.created_at}] {msg.author} ({msg.author.id}):" " {\n")
                    # 內容
                    if has_content:
                        indented_content = "\n".join(f"    {line}" for line in snap_content.splitlines())
                        await f.write(indented_content + "\n")
                    # 附件
                    await process_attachments_and_stickers(snap_attachments, [], indent="     ^ ")
                    await f.write("}\n")

    await download_queue.join()

    for _ in range(worker_count):
        await download_queue.put(None)
    await asyncio.gather(*workers)

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
