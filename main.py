import requests
import json
import os
import time
import re
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# -------------------------
# CONFIG
# -------------------------
with open("config.json") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
CHANNEL_ID = config["channel_id"]
SOURCE_URL = config["source_url"]
MAX_PER_DAY = config["max_per_day"]

bot = Bot(token=BOT_TOKEN)

# -------------------------
# LOAD POSTED
# -------------------------
if os.path.exists("posted.txt"):
    with open("posted.txt", "r") as f:
        posted = set(f.read().splitlines())
else:
    posted = set()

# -------------------------
# SOURCES
# -------------------------
def get_sources():
    data = []

    # GitHub
    try:
        data += requests.get(SOURCE_URL, timeout=10).text.splitlines()
    except:
        pass

    # Proxy API fallback
    try:
        url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all"
        data += requests.get(url, timeout=10).text.splitlines()
    except:
        pass

    return data

# -------------------------
# NORMALIZER (ALL FORMATS)
# -------------------------
def normalize(line):
    line = line.strip()
    if not line:
        return None

    server = port = secret = None

    # Format 1: server=...&port=...&secret=...
    match = re.search(r"server=([^&]+)&port=([^&]+)&secret=([^\s]+)", line)
    if match:
        server = match.group(1).strip()
        port = match.group(2).strip()
        secret = match.group(3).strip()
    else:
        # Format 2: ip:port:secret
        parts = line.split(":")
        if len(parts) == 3:
            server, port, secret = parts[0].strip(), parts[1].strip(), parts[2].strip()
        else:
            return None

    if not server or not port or not secret:
        return None

    if not port.isdigit():
        return None

    return (server, port, secret)

# -------------------------
# PROXY TESTER (FAST MODE)
# -------------------------
def test_proxy(server, port):
    try:
        proxies = {
            "http": f"http://{server}:{port}",
            "https": f"http://{server}:{port}"
        }

        start = time.time()

        r = requests.get(
            "https://api.ipify.org",
            proxies=proxies,
            timeout=8
        )

        speed = time.time() - start

        if r.status_code == 200:
            return True, speed

        return False, None

    except:
        return False, None

# -------------------------
# FETCH DATA
# -------------------------
raw_data = get_sources()

clean = []

for line in raw_data:
    proxy = normalize(line)
    if proxy:
        clean.append(proxy)

# -------------------------
# TEST + FILTER
# -------------------------
valid = []

for server, port, secret in clean:

    key = f"{server}:{port}:{secret}"

    if key in posted:
        continue

    ok, speed = test_proxy(server, port)

    if not ok:
        continue

    # ACCEPT ONLY <= 8s
    if speed <= 8.0:

        # CATEGORY
        if speed < 1.5:
            category = "FAST 🟢"
        elif speed < 4:
            category = "MEDIUM 🟡"
        else:
            category = "SLOW 🟠"

        valid.append((server, port, secret, speed, category, key))

# -------------------------
# SORT (FAST FIRST)
# -------------------------
valid.sort(key=lambda x: x[3])

valid = valid[:MAX_PER_DAY]

# -------------------------
# SEND TO TELEGRAM
# -------------------------
count = 0

for server, port, secret, speed, category, key in valid:

    count += 1

    message = f"""🔥 ACTIVE PROXY #{count}

🌐 Server: {server}
🔌 Port: {port}
🔑 Secret: {secret}

⚡ Speed: {category} ({round(speed, 2)}s)

⚡ @ProxyMTProto44"""

    tg_link = f"tg://proxy?server={server}&port={port}&secret={secret}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Connect Proxy", url=tg_link)]
    ])

    try:
        sent = bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            reply_markup=keyboard
        )
    except Exception as e:
        print("Telegram error:", e)
        continue

    posted.add(key)

    with open("messages.txt", "a") as f:
        f.write(f"{sent.message_id}|{int(time.time())}\n")

# -------------------------
# SAVE STATE
# -------------------------
with open("posted.txt", "w") as f:
    f.write("\n".join(posted))

print(f"Done. Posted {count} proxies.")
