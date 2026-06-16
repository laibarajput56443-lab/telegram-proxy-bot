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
def get_sources():
    data = []

    # GitHub source
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

    # basic validation only
    if not server or not port or not secret:
        return None

    if not port.isdigit():
        return None

    return f"{server}:{port}:{secret}"

# -------------------------
# FETCH DATA
# -------------------------
raw_data = get_sources()

clean_proxies = []

for line in raw_data:
    proxy = normalize(line)
    if proxy:
        clean_proxies.append(proxy)

# -------------------------
# FILTER + DEDUPLICATE
# -------------------------
valid_proxies = []

for proxy in clean_proxies:
    if proxy in posted:
        continue
    valid_proxies.append(proxy)

valid_proxies = valid_proxies[:MAX_PER_DAY]

# -------------------------
# SEND TO TELEGRAM
# -------------------------
count = 0

for proxy in valid_proxies:
    try:
        server, port, secret = proxy.split(":")
    except:
        continue

    count += 1

    message = f"""🔥 ACTIVE PROXY #{count}

🌐 Server: {server}
🔌 Port: {port}
🔑 Secret: {secret}

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
        print("Telegram send failed:", e)
        continue

    posted.add(proxy)

    with open("messages.txt", "a") as f:
        f.write(f"{sent.message_id}|{int(time.time())}\n")

# -------------------------
# SAVE STATE
# -------------------------
with open("posted.txt", "w") as f:
    f.write("\n".join(posted))

print(f"Done. Posted {count} active proxies.")
