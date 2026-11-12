# 🤖 Telegram Auto Forward Userbot

Apne Telegram account se chalne wala userbot. Jis bhi **channel/group** mein aapka account hai,
wahan ke sirf **video / file** messages aapke set kiye hue channel par auto forward ho jaate hain.

## ✨ Features
- `/setf <chat_id>` se destination channel set karo
- Sirf video / file forward (text, photo etc. ignore)
- `copy` mode (bina "Forwarded from") ya `forward` mode
- Source whitelist aur block list
- Queue + delay + FloodWait handling
- Poora control commands se (apne account se)

## 🔧 Environment Variables
| Variable | Kaam |
|---|---|
| `API_ID` | my.telegram.org se |
| `API_HASH` | my.telegram.org se |
| `SESSION_STRING` | Pyrogram string session |
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

**Heroku / Railway / Koyeb / Render** – repo connect karo, env variables set karo, `worker` dyno/process chalao (Procfile ya Dockerfile use hoga).

## 📜 Commands
Ye commands **aapke apne account** se kisi bhi chat ya Saved Messages mein bhejo.

| Command | Kaam |
|---|---|
| `/setf <chat_id>` | Destination channel set karo (ex: `/setf -1003951110216`) |
| `/unsetf` | Destination hatao |
| `/fon` / `/foff` | Forwarding on/off |
| `/fmode copy\|forward` | Copy (no tag) ya forward |
| `/ftype video\|file\|both` | Kya forward karna hai |
| `/fdelay <sec>` | Forwards ke beech delay |
| `/addsrc <id>` / `/rmsrc <id>` | Sirf chuni hui chats se forward |
| `/block <id>` / `/unblock <id>` | Chat block/unblock |
| `/srclist` | Source & blocked list |
| `/fid` | Current chat ki ID |
| `/fstatus` | Status + total forwarded |
| `/fclear` | Pending queue saaf |
| `/fhelp` | Help |

## ⚠️ Zaroori baatein
- Destination channel mein aapka account **admin (post permission)** hona chahiye.
- `SESSION_STRING` kisi ke saath share mat karo, ye aapke account ka full access hai.
- Userbot Telegram ToS ki grey area mein aata hai; zyada aggressive forwarding (delay 0) se account limit ho sakta hai.
- Protected (forward-restricted) channels se copy/forward fail ho sakta hai.

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
