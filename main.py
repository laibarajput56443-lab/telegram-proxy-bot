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
# LOAD POSTED PROXIES
# -------------------------
if os.path.exists("posted.txt"):
    with open("posted.txt", "r") as f:
        posted = set(f.read().splitlines())
else:
    posted = set()

# -------------------------
# SOURCES
# -------------------------
def get_github():
    try:
        return requests.get(SOURCE_URL, timeout=10).text.splitlines()
    except:
        return []

def get_api():
    try:
        url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all"
        return requests.get(url, timeout=10).text.splitlines()
    except:
        return []

def get_fallback():
    return [
        "1.1.1.1:80:demo",
        "8.8.8.8:8080:demo"
    ]

def get_all_sources():
    data = []
    data += get_github()
    data += get_api()
    data += get_fallback()
    return data

# -------------------------
# NORMALIZER
# -------------------------
def normalize(line):
    line = line.strip()
    if not line:
        return None

    server = port = secret = None

    match = re.search(r"server=([^&]+)&port=([^&]+)&secret=([^\s]+)", line)

    if match:
        server = match.group(1).strip()
        port = match.group(2).strip()
        secret = match.group(3).strip()
    else:
        parts = line.split(":")
        if len(parts) == 3:
            server, port, secret = parts
        else:
            return None

    if not port.isdigit():
        return None

    return f"{server}:{port}:{secret}"

# -------------------------
# FAST PROXY TESTER
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
            timeout=5
        )

        speed = time.time() - start

        if r.status_code == 200:
            return True, speed
        return False, None

    except:
        return False, None

# -------------------------
# FETCH + CLEAN
# -------------------------
raw_data = get_all_sources()

clean_proxies = []

for line in raw_data:
    proxy = normalize(line)
    if proxy:
        clean_proxies.append(proxy)

# -------------------------
# BUILD VALID LIST
# -------------------------
valid = []

for item in clean_proxies:
    server, port, secret = item.split(":")

    key = item
    if key in posted:
        continue

    ok, speed = test_proxy(server, port)

    if ok:
        if speed < 3:  # FAST + MEDIUM allowed
            valid.append((server, port, secret, speed, key))

# -------------------------
# SORT BY SPEED
# -------------------------
valid.sort(key=lambda x: x[3])

valid = valid[:MAX_PER_DAY]

# -------------------------
# SEND TO TELEGRAM
# -------------------------
count = 0

for server, port, secret, speed, key in valid:
    count += 1

    if speed < 1.5:
        speed_tag = "FAST 🟢"
    else:
        speed_tag = "MEDIUM 🟡"

    message = f"""🔥 PREMIUM LIVE PROXY #{count}

🌐 Server: {server}
🔌 Port: {port}
🔑 Secret: {secret}

⚡ Speed: {speed_tag}

⚡ @ProxyMTProto44"""

    tg_link = f"tg://proxy?server={server}&port={port}&secret={secret}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Connect Now", url=tg_link)]
    ])

    try:
        sent = bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            reply_markup=keyboard
        )
    except:
        continue

    posted.add(key)

    with open("messages.txt", "a") as f:
        f.write(f"{sent.message_id}|{int(time.time())}\n")

# -------------------------
# SAVE STATE
# -------------------------
with open("posted.txt", "w") as f:
    f.write("\n".join(posted))

print(f"Done. Posted {count} premium proxies.")
