"""
Telegram Auto Forward Userbot (Pyrogram)
- Aapke apne account se chalta hai (SESSION_STRING env variable)
- Jis bhi channel/group mein aapka account hai, wahan ke VIDEO / FILE messages
  aapke set kiye hue channel par forward ho jaate hain. Baaki koi msg nahi.

ENV VARIABLES:
    API_ID          -> my.telegram.org se
    API_HASH        -> my.telegram.org se
    SESSION_STRING  -> Pyrogram string session
"""

import os
import json
import asyncio
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait

try:  # local run ke liye .env support (optional)
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

CONFIG_FILE = os.environ.get("CONFIG_FILE", "config.json")

DEFAULT_CONFIG = {
    "dest": None,          # destination chat id
    "enabled": True,       # forwarding on/off
    "mode": "copy",        # copy (bina "Forwarded from") | forward
    "types": "both",       # video | file | both
    "sources": [],         # agar khali hai to sab chats se; warna sirf inhi se
    "blocked": [],         # in chats se kabhi forward nahi
    "delay": 2,            # har forward ke beech seconds (floodwait se bachne ke liye)
    "count": 0,            # total forwarded
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
            return {**DEFAULT_CONFIG, **data}
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


cfg = load_config()
app = Client("autoforward", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
queue: asyncio.Queue = asyncio.Queue()

# Sirf aapke khud ke bheje hue commands chalenge
cmd = lambda c: filters.me & filters.command(c, prefixes="/")


def parse_id(message):
    if len(message.command) < 2:
        return None
    try:
        return int(message.command[1])
    except ValueError:
        return None


# ───────────────────────── COMMANDS ─────────────────────────

@app.on_message(cmd("setf"), group=0)
async def set_dest(client, message):
    chat_id = parse_id(message)
    if chat_id is None:
        return await message.edit_text("❌ Usage: `/setf -1001234567890`")
    try:
        chat = await client.get_chat(chat_id)
    except Exception as e:
        return await message.edit_text(f"❌ Chat nahi mila / access nahi hai:\n`{e}`")
    cfg["dest"] = chat_id
    save_config()
    await message.edit_text(f"✅ Destination set:\n**{chat.title}** (`{chat_id}`)")


@app.on_message(cmd("unsetf"), group=0)
async def unset_dest(client, message):
    cfg["dest"] = None
    save_config()
    await message.edit_text("🗑 Destination hata diya. Forwarding ruk gayi.")


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


@app.on_message(cmd("ftype"), group=0)
async def f_type(client, message):
    if len(message.command) < 2 or message.command[1].lower() not in ("video", "file", "both"):
        return await message.edit_text("Usage: `/ftype video` | `/ftype file` | `/ftype both`")
    cfg["types"] = message.command[1].lower()
    save_config()
    await message.edit_text(f"✅ Type: **{cfg['types']}**")


@app.on_message(cmd("fdelay"), group=0)
async def f_delay(client, message):
    try:
        sec = max(0, int(message.command[1]))
    except Exception:
        return await message.edit_text("Usage: `/fdelay 3` (seconds)")
    cfg["delay"] = sec
    save_config()
    await message.edit_text(f"✅ Delay: **{sec}s**")


@app.on_message(cmd("addsrc"), group=0)
async def add_src(client, message):
    chat_id = parse_id(message)
    if chat_id is None:
        return await message.edit_text("Usage: `/addsrc -100xxxxxxxxxx`")
    if chat_id not in cfg["sources"]:
        cfg["sources"].append(chat_id)
        save_config()
    await message.edit_text(f"✅ Source add: `{chat_id}`\nAb sirf source list wali chats se forward hoga.")


@app.on_message(cmd("rmsrc"), group=0)
async def rm_src(client, message):
    chat_id = parse_id(message)
    if chat_id in cfg["sources"]:
        cfg["sources"].remove(chat_id)
        save_config()
        return await message.edit_text(f"🗑 Source hata diya: `{chat_id}`")
    await message.edit_text("❌ Ye source list mein nahi hai.")


@app.on_message(cmd("srclist"), group=0)
async def src_list(client, message):
    src = "\n".join(f"• `{i}`" for i in cfg["sources"]) or "Khali (sab chats se forward hota hai)"
    blk = "\n".join(f"• `{i}`" for i in cfg["blocked"]) or "Khali"
    await message.edit_text(f"📥 **Sources:**\n{src}\n\n🚫 **Blocked:**\n{blk}")


@app.on_message(cmd("block"), group=0)
async def block(client, message):
    chat_id = parse_id(message)
    if chat_id is None:
        return await message.edit_text("Usage: `/block -100xxxxxxxxxx`")
    if chat_id not in cfg["blocked"]:
        cfg["blocked"].append(chat_id)
        save_config()
    await message.edit_text(f"🚫 Blocked: `{chat_id}`")


@app.on_message(cmd("unblock"), group=0)
async def unblock(client, message):
    chat_id = parse_id(message)
    if chat_id in cfg["blocked"]:
        cfg["blocked"].remove(chat_id)
        save_config()
        return await message.edit_text(f"✅ Unblocked: `{chat_id}`")
    await message.edit_text("❌ Ye blocked list mein nahi hai.")


@app.on_message(cmd("fid"), group=0)
async def get_id(client, message):
    await message.edit_text(f"🆔 Is chat ki ID: `{message.chat.id}`")


@app.on_message(cmd("fstatus"), group=0)
async def status(client, message):
    await message.edit_text(
        "📊 **Auto Forward Status**\n\n"
        f"• Status: {'ON ✅' if cfg['enabled'] else 'OFF ⏸'}\n"
        f"• Destination: `{cfg['dest']}`\n"
        f"• Mode: `{cfg['mode']}`\n"
        f"• Type: `{cfg['types']}`\n"
        f"• Delay: `{cfg['delay']}s`\n"
        f"• Sources: `{len(cfg['sources'])}` | Blocked: `{len(cfg['blocked'])}`\n"
        f"• Queue: `{queue.qsize()}`\n"
        f"• Total forwarded: `{cfg['count']}`"
    )


@app.on_message(cmd("fhelp"), group=0)
async def f_help(client, message):
    await message.edit_text(
        "🤖 **Auto Forward Commands**\n\n"
        "`/setf <chat_id>` – destination channel set karo\n"
        "`/unsetf` – destination hatao\n"
        "`/fon` / `/foff` – forwarding on/off\n"
        "`/fmode copy|forward` – copy (no tag) ya forward\n"
        "`/ftype video|file|both` – kya forward karna hai\n"
        "`/fdelay <sec>` – forwards ke beech delay\n"
        "`/addsrc <id>` / `/rmsrc <id>` – sirf chuni hui chats se\n"
        "`/block <id>` / `/unblock <id>` – chat block/unblock\n"
        "`/srclist` – source & blocked list\n"
        "`/fid` – current chat ki ID\n"
        "`/fstatus` – poora status\n"
        "`/fclear` – pending queue saaf karo"
    )


@app.on_message(cmd("fclear"), group=0)
async def f_clear(client, message):
    n = 0
    while not queue.empty():
        queue.get_nowait()
        n += 1
    await message.edit_text(f"🧹 Queue saaf: `{n}` pending hataye.")


# ───────────────────── AUTO FORWARD LOGIC ─────────────────────

def is_wanted(message) -> bool:
    is_video = bool(message.video) or (
        message.document and (message.document.mime_type or "").startswith("video/")
    )
    is_file = bool(message.document) and not is_video
    t = cfg["types"]
    if t == "video":
        return is_video
    if t == "file":
        return is_file
    return is_video or is_file


@app.on_message(
    (filters.channel | filters.group) & (filters.video | filters.document) & ~filters.me,
    group=1,
)
async def collector(client, message):
    if not cfg["enabled"] or not cfg["dest"]:
        return
    cid = message.chat.id
    if cid == cfg["dest"] or cid in cfg["blocked"]:
        return
    if cfg["sources"] and cid not in cfg["sources"]:
        return
    if not is_wanted(message):
        return
    await queue.put((cid, message.id))


async def worker():
    while True:
        chat_id, msg_id = await queue.get()
        try:
            if not cfg["dest"]:
                continue
            if cfg["mode"] == "copy":
                await app.copy_message(cfg["dest"], chat_id, msg_id)
            else:
                await app.forward_messages(cfg["dest"], chat_id, msg_id)
            cfg["count"] += 1
            save_config()
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            await queue.put((chat_id, msg_id))  # dobara try
        except Exception as e:
            print(f"[ERROR] {chat_id}/{msg_id}: {e}")
        await asyncio.sleep(cfg["delay"])


async def main():
    await app.start()
    asyncio.create_task(worker())
    me = await app.get_me()
    print(f"Auto Forward started as {me.first_name} ({me.id})")
    await idle()
    await app.stop()


if __name__ == "__main__":
    app.run(main())
