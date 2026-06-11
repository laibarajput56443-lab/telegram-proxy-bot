import requests
import json
import os
import time
import re
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# Load config
with open("config.json") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
CHANNEL_ID = config["channel_id"]
SOURCE_URL = config["source_url"]
MAX_PER_DAY = config["max_per_day"]

bot = Bot(token=BOT_TOKEN)

# Load already posted proxies
if os.path.exists("posted.txt"):
    with open("posted.txt", "r") as f:
        posted = set(f.read().splitlines())
else:
    posted = set()

# Fetch proxy list
data = requests.get(SOURCE_URL, timeout=10).text.splitlines()

new_proxies = []

for line in data:
    line = line.strip()
    if not line:
        continue

    # -------------------------------
    # MULTI-FORMAT PROXY PARSER
    # -------------------------------

    server = port = secret = None

    # Format 1: tg://proxy or server=...&port=...&secret=...
    match = re.search(r"server=([^&]+)&port=([^&]+)&secret=([^\s]+)", line)

    if match:
        server = match.group(1).strip()
        port = match.group(2).strip()
        secret = match.group(3).strip()

    else:
        # Format 2: ip:port:secret (GitHub repo format)
        parts = line.split(":")
        if len(parts) == 3:
            server, port, secret = parts[0].strip(), parts[1].strip(), parts[2].strip()
        else:
            continue

    # safety check
    if not port.isdigit():
        continue

    key = f"{server}:{port}:{secret}"

    if key not in posted:
        new_proxies.append((server, port, secret, key))

# Limit per day
new_proxies = new_proxies[:MAX_PER_DAY]

count = 0

for server, port, secret, key in new_proxies:
    count += 1

    message = f"""🌐 Proxy #{count}

Server: {server}
Port: {port}
Secret: {secret}

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
        print("Failed to send message:", e)
        continue

    posted.add(key)

    # Save message id + timestamp (optional tracking)
    with open("messages.txt", "a") as f:
        f.write(f"{sent.message_id}|{int(time.time())}\n")

# Save updated posted list
with open("posted.txt", "w") as f:
    f.write("\n".join(posted))

print(f"Done. Posted {count} new proxies.")
