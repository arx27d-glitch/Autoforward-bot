"""
Telegram Auto Forward Userbot (Pyrogram)

- Aapke apne account se chalta hai (SESSION_STRING).
- Sirf wahi channels/groups se forward karta hai jo aapne SET kiye hain (whitelist).
- Sirf VIDEO files (mp4, mkv, avi, mov, webm ... sab video) forward hoti hain.
- Sirf un chats se jahan forwarding allowed hai (protected content skip).
- Destination channel aur Log group ENV variable se aate hain.
- Saare commands sirf aapke Saved Messages ya Log Group mein chalte hain.

ENV VARIABLES:
    API_ID, API_HASH, SESSION_STRING
    DEST_CHAT_ID    -> jis channel mein forward karna hai
    LOG_GROUP_ID    -> aapka log/command group
    SOURCE_CHATS    -> (optional) comma separated source chat ids
    DELAY           -> (optional) forwards ke beech seconds, default 2
"""

import os
import re
import json
import asyncio
from pyrogram import Client, filters, idle
from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait

try:  # local run ke liye .env support (optional)
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
DEST_CHAT_ID = int(os.environ["DEST_CHAT_ID"])
LOG_GROUP_ID = int(os.environ["LOG_GROUP_ID"])
ENV_SOURCES = {
    int(x) for x in re.split(r"[,\s]+", os.environ.get("SOURCE_CHATS", ""))
    if x.lstrip("-").isdigit()
}

CONFIG_FILE = os.environ.get("CONFIG_FILE", "config.json")
MAX_SENT = 5000

VIDEO_EXT = (
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v",
    ".ts", ".3gp", ".mpg", ".mpeg", ".mts", ".m2ts", ".vob", ".ogv",
)

DEFAULT_CONFIG = {
    "enabled": True,
    "mode": "copy",        # copy (bina "Forwarded from") | forward
    "delay": int(os.environ.get("DELAY", 2)),
    "dedupe": True,        # same video dobara forward na ho
    "log": True,           # har forward ka log, log group mein
    "sources": [],         # /addsrc se add hue source chats
    "sent": [],            # forward ho chuki files ke unique ids
    "count": 0,
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f)


cfg = load_config()
seen = set(cfg["sent"])
app = Client("autoforward", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
queue: asyncio.Queue = asyncio.Queue()


def all_sources() -> set:
    return set(cfg["sources"]) | ENV_SOURCES


async def log(text: str):
    try:
        await app.send_message(LOG_GROUP_ID, text, disable_web_page_preview=True)
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        print(f"[LOG ERROR] {e}")


# ───────────── Command access: sirf Saved Messages / Log Group ─────────────

async def _allowed(_, client, message):
    return bool(message.chat) and message.chat.id in (client.me.id, LOG_GROUP_ID)


allowed_chat = filters.create(_allowed)


def cmd(name):
    return filters.me & allowed_chat & filters.command(name, prefixes="/")


async def resolve_chat(client, arg: str):
    try:
        key = int(arg)
    except ValueError:
        key = arg.replace("https://t.me/", "").replace("http://t.me/", "").lstrip("@")
    return await client.get_chat(key)


def is_protected(message) -> bool:
    chat = message.chat
    return bool(
        getattr(message, "has_protected_content", False)
        or getattr(chat, "has_protected_content", False)
    )


def is_video(message) -> bool:
    if message.video:
        return True
    d = message.document
    if d:
        mime = (d.mime_type or "").lower()
        name = (d.file_name or "").lower()
        return mime.startswith("video/") or name.endswith(VIDEO_EXT)
    return False


def file_key(message):
    media = message.video or message.document
    return media.file_unique_id if media else None


# ───────────────────────────── COMMANDS ─────────────────────────────

@app.on_message(cmd("addsrc"), group=0)
async def add_src(client, message):
    if len(message.command) < 2:
        return await message.edit_text(
            "Usage: `/addsrc -100xxxxxxxxxx` (ya @username / t.me link)\n"
            "Chat ID chahiye to `/fchats` use karo."
        )
    try:
        chat = await resolve_chat(client, message.command[1])
    except Exception as e:
        return await message.edit_text(f"❌ Chat nahi mila (aap member hain?):\n`{e}`")
    if chat.id == DEST_CHAT_ID:
        return await message.edit_text("❌ Destination ko source nahi bana sakte.")
    if chat.id not in cfg["sources"]:
        cfg["sources"].append(chat.id)
        save_config()
    warn = ""
    if getattr(chat, "has_protected_content", False):
        warn = "\n⚠️ Is chat mein forwarding band hai, isliye isse kuch forward nahi hoga."
    await message.edit_text(f"✅ Source add: **{chat.title}** (`{chat.id}`){warn}")


@app.on_message(cmd("rmsrc"), group=0)
async def rm_src(client, message):
    if len(message.command) < 2:
        return await message.edit_text("Usage: `/rmsrc -100xxxxxxxxxx`")
    arg = message.command[1]
    try:
        cid = int(arg)
    except ValueError:
        try:
            cid = (await resolve_chat(client, arg)).id
        except Exception as e:
            return await message.edit_text(f"❌ `{e}`")
    if cid in cfg["sources"]:
        cfg["sources"].remove(cid)
        save_config()
        return await message.edit_text(f"🗑 Source hata diya: `{cid}`")
    if cid in ENV_SOURCES:
        return await message.edit_text("ℹ️ Ye SOURCE_CHATS env variable mein hai, wahan se hatao.")
    await message.edit_text("❌ Ye source list mein nahi hai.")


@app.on_message(cmd("srclist"), group=0)
async def src_list(client, message):
    ids = sorted(all_sources())
    if not ids:
        return await message.edit_text("📥 Koi source set nahi hai. `/addsrc <id>` se add karo.")
    lines = []
    for cid in ids:
        try:
            c = await client.get_chat(cid)
            lock = " 🔒" if getattr(c, "has_protected_content", False) else ""
            lines.append(f"• {c.title}{lock} — `{cid}`")
        except Exception:
            lines.append(f"• (access nahi) — `{cid}`")
    await message.edit_text("📥 **Source chats:**\n" + "\n".join(lines))


@app.on_message(cmd("fchats"), group=0)
async def list_chats(client, message):
    await message.edit_text("⏳ Aapke groups/channels load ho rahe hain...")
    lines = []
    async for d in client.get_dialogs():
        c = d.chat
        if c.type in (ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL):
            icon = "🔒" if getattr(c, "has_protected_content", False) else "✅"
            lines.append(f"{icon} {c.title} — `{c.id}`")
    if not lines:
        return await message.edit_text("Koi group/channel nahi mila.")
    text, chunks = "", []
    for line in lines:
        if len(text) + len(line) > 3800:
            chunks.append(text)
            text = ""
        text += line + "\n"
    chunks.append(text)
    await message.edit_text("📂 **Aapke chats** (✅ forward allowed, 🔒 protected)\n\n" + chunks[0])
    for extra in chunks[1:]:
        await message.reply_text(extra)


@app.on_message(cmd("fon"), group=0)
async def f_on(client, message):
    cfg["enabled"] = True
    save_config()
    await message.edit_text("▶️ Auto forward **ON**")


@app.on_message(cmd("foff"), group=0)
async def f_off(client, message):
    cfg["enabled"] = False
    save_config()
    await message.edit_text("⏸ Auto forward **OFF**")


@app.on_message(cmd("fmode"), group=0)
async def f_mode(client, message):
    if len(message.command) < 2 or message.command[1].lower() not in ("copy", "forward"):
        return await message.edit_text(
            "Usage: `/fmode copy` (bina source tag) ya `/fmode forward` (Forwarded from ke saath)"
        )
    cfg["mode"] = message.command[1].lower()
    save_config()
    await message.edit_text(f"✅ Mode: **{cfg['mode']}**")


@app.on_message(cmd("fdelay"), group=0)
async def f_delay(client, message):
    try:
        sec = max(0, int(message.command[1]))
    except Exception:
        return await message.edit_text("Usage: `/fdelay 3` (seconds)")
    cfg["delay"] = sec
    save_config()
    await message.edit_text(f"✅ Delay: **{sec}s**")


@app.on_message(cmd("fdup"), group=0)
async def f_dup(client, message):
    arg = message.command[1].lower() if len(message.command) > 1 else ""
    if arg not in ("on", "off"):
        return await message.edit_text("Usage: `/fdup on` ya `/fdup off` (duplicate video skip)")
    cfg["dedupe"] = arg == "on"
    save_config()
    await message.edit_text(f"✅ Duplicate filter: **{arg.upper()}**")


@app.on_message(cmd("flog"), group=0)
async def f_log(client, message):
    arg = message.command[1].lower() if len(message.command) > 1 else ""
    if arg not in ("on", "off"):
        return await message.edit_text("Usage: `/flog on` ya `/flog off` (forward logs)")
    cfg["log"] = arg == "on"
    save_config()
    await message.edit_text(f"✅ Forward logs: **{arg.upper()}**")


@app.on_message(cmd("fclear"), group=0)
async def f_clear(client, message):
    n = 0
    while not queue.empty():
        queue.get_nowait()
        n += 1
    await message.edit_text(f"🧹 Queue saaf: `{n}` pending hataye.")


@app.on_message(cmd("fresetdup"), group=0)
async def f_resetdup(client, message):
    seen.clear()
    cfg["sent"] = []
    save_config()
    await message.edit_text("🧹 Duplicate history saaf kar di.")


@app.on_message(cmd("fid"), group=0)
async def get_id(client, message):
    await message.edit_text(f"🆔 Is chat ki ID: `{message.chat.id}`")


@app.on_message(cmd("fstatus"), group=0)
async def status(client, message):
    await message.edit_text(
        "📊 **Auto Forward Status**\n\n"
        f"• Status: {'ON ✅' if cfg['enabled'] else 'OFF ⏸'}\n"
        f"• Destination: `{DEST_CHAT_ID}`\n"
        f"• Log group: `{LOG_GROUP_ID}`\n"
        f"• Sources: `{len(all_sources())}`\n"
        f"• Mode: `{cfg['mode']}` | Delay: `{cfg['delay']}s`\n"
        f"• Duplicate filter: `{'ON' if cfg['dedupe'] else 'OFF'}` | Logs: `{'ON' if cfg['log'] else 'OFF'}`\n"
        f"• Queue: `{queue.qsize()}`\n"
        f"• Total forwarded: `{cfg['count']}`"
    )


@app.on_message(cmd("fhelp"), group=0)
async def f_help(client, message):
    await message.edit_text(
        "🤖 **Auto Forward Commands**\n\n"
        "`/addsrc <id|@user>` – source chat add karo\n"
        "`/rmsrc <id>` – source hatao\n"
        "`/srclist` – saare sources\n"
        "`/fchats` – aapke saare groups/channels + IDs\n"
        "`/fon` / `/foff` – forwarding on/off\n"
        "`/fmode copy|forward` – copy (no tag) ya forward\n"
        "`/fdelay <sec>` – forwards ke beech delay\n"
        "`/fdup on|off` – duplicate video filter\n"
        "`/flog on|off` – forward logs\n"
        "`/fresetdup` – duplicate history saaf\n"
        "`/fclear` – pending queue saaf\n"
        "`/fid` – current chat ki ID\n"
        "`/fstatus` – poora status"
    )


# ───────────────────────── AUTO FORWARD LOGIC ─────────────────────────

@app.on_message(
    (filters.channel | filters.group) & (filters.video | filters.document) & ~filters.me,
    group=1,
)
async def collector(client, message):
    if not cfg["enabled"]:
        return
    cid = message.chat.id
    if cid == DEST_CHAT_ID or cid == LOG_GROUP_ID:
        return
    if cid not in all_sources():          # sirf set kiye hue chats
        return
    if is_protected(message):             # forwarding band wali chats skip
        return
    if not is_video(message):             # sirf video files
        return
    key = file_key(message)
    if cfg["dedupe"] and key and key in seen:
        return
    await queue.put((cid, message.id, message.chat.title or str(cid), key))


async def worker():
    while True:
        cid, mid, title, key = await queue.get()
        try:
            if cfg["mode"] == "copy":
                await app.copy_message(DEST_CHAT_ID, cid, mid)
            else:
                await app.forward_messages(DEST_CHAT_ID, cid, mid)
            cfg["count"] += 1
            if key:
                seen.add(key)
                cfg["sent"].append(key)
                if len(cfg["sent"]) > MAX_SENT:
                    removed = cfg["sent"][: len(cfg["sent"]) - MAX_SENT]
                    cfg["sent"] = cfg["sent"][-MAX_SENT:]
                    seen.difference_update(removed)
            save_config()
            if cfg["log"]:
                await log(f"✅ Forwarded from **{title}** (`{cid}`) — msg `{mid}`")
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            await queue.put((cid, mid, title, key))
            continue
        except Exception as e:
            print(f"[ERROR] {cid}/{mid}: {e}")
            await log(f"❌ Forward fail: **{title}** (`{cid}`) msg `{mid}`\n`{e}`")
        await asyncio.sleep(cfg["delay"])


async def main():
    await app.start()
    # peers cache karne ke liye dialogs load
    try:
        async for _ in app.get_dialogs():
            pass
    except Exception as e:
        print(f"[WARN] dialogs load: {e}")
    asyncio.create_task(worker())
    me = await app.get_me()
    print(f"Auto Forward started as {me.first_name} ({me.id})")

    dest_note = ""
    try:
        d = await app.get_chat(DEST_CHAT_ID)
        dest_note = f"**{d.title}** (`{DEST_CHAT_ID}`)"
    except Exception as e:
        dest_note = f"`{DEST_CHAT_ID}` ⚠️ access error: `{e}`"
    await log(
        "🚀 **Auto Forward Bot started**\n"
        f"• Destination: {dest_note}\n"
        f"• Sources: `{len(all_sources())}`\n"
        f"• Status: {'ON' if cfg['enabled'] else 'OFF'}\n"
        "Commands ke liye `/fhelp`"
    )
    await idle()
    await app.stop()


if __name__ == "__main__":
    app.run(main())
