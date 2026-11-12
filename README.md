# 🤖 Telegram Auto Forward Userbot

Apne Telegram account se chalne wala userbot. Aapne jin **channels/groups** ko source set kiya hai,
sirf wahin ki **video files** (mp4, mkv, avi, mov, webm ... sab) aapke channel par auto forward hoti hain.

## ✨ Features
- Sirf **set kiye hue** source chats se forward, baaki kisi se nahi
- Sirf **video files** (video message + video documents)
- Sirf un chats se jahan **forwarding allowed** hai (protected content skip)
- Destination channel aur Log group **ENV variable** se
- Saare commands sirf **Saved Messages ya Log Group** mein chalte hain
- Duplicate video filter, queue, delay, FloodWait handling
- Har forward ka log, log group mein

## 🔧 Environment Variables
| Variable | Kaam |
|---|---|
| `API_ID` | my.telegram.org se |
| `API_HASH` | my.telegram.org se |
| `SESSION_STRING` | Pyrogram string session |
| `DEST_CHAT_ID` | Jis channel mein forward karna hai |
| `LOG_GROUP_ID` | Log + command group |
| `SOURCE_CHATS` | (optional) source chat ids, comma separated |
| `DELAY` | (optional) forwards ke beech seconds, default 2 |
| `CONFIG_FILE` | (optional) config.json ka path |

## 🔑 Session String kaise banayein
```bash
pip install -r requirements.txt
python generate_session.py
```

## 🚀 Run karna
**Local**
```bash
cp .env.sample .env      # values bharo
pip install -r requirements.txt
python main.py
```

**Docker**
```bash
docker build -t autoforward .
docker run -d --env-file .env -v $(pwd)/data:/data -e CONFIG_FILE=/data/config.json autoforward
```

**Heroku / Railway / Koyeb / Render** – repo connect karo, env variables set karo, `worker` process chalao.

## 📜 Commands
Sirf **Saved Messages ya Log Group** mein, aapke apne account se.

| Command | Kaam |
|---|---|
| `/addsrc <id\|@user>` | Source chat add karo |
| `/rmsrc <id>` | Source hatao |
| `/srclist` | Saare sources |
| `/fchats` | Aapke saare groups/channels aur IDs (🔒 = forward band) |
| `/fon` / `/foff` | Forwarding on/off |
| `/fmode copy\|forward` | Copy (no tag) ya forward |
| `/fdelay <sec>` | Forwards ke beech delay |
| `/fdup on\|off` | Duplicate video filter |
| `/flog on\|off` | Forward logs |
| `/fresetdup` | Duplicate history saaf |
| `/fclear` | Pending queue saaf |
| `/fid` | Current chat ki ID |
| `/fstatus` | Status + total forwarded |
| `/fhelp` | Help |

## ⚠️ Zaroori baatein
- Destination channel mein aapka account **admin (post permission)** hona chahiye.
- Aap source chats ke **member** hone chahiye.
- `SESSION_STRING` kisi ke saath share mat karo, ye aapke account ka full access hai.
- Zyada aggressive forwarding (delay 0) se account limit ho sakta hai.

## 📁 Structure
```
autoforward-bot/
├── main.py
├── generate_session.py
├── requirements.txt
├── Dockerfile
├── Procfile
├── heroku.yml
├── app.json
├── .env.sample
├── .gitignore
├── .dockerignore
├── LICENSE
└── README.md
```

## 📄 License
MIT
