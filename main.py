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
data = requests.get(SOURCE_URL).text.splitlines()

new_proxies = []

for line in data:
    line = line.strip()
    if not line:
        continue

    # Extract MTProto proxy from tg:// or https links
    match = re.search(r"server=([^&]+)&port=([^&]+)&secret=([^\s]+)", line)

    if not match:
        continue

    server = match.group(1)
    port = match.group(2)
    secret = match.group(3)

    key = f"{server}:{port}:{secret}"

    if key not in posted:
        new_proxies.append((server, port, secret, key))

# Limit per day
new_proxies = new_proxies[:MAX_PER_DAY]

count = 0

for server, port, secret, key in new_proxies:
    count += 1

message = f"""Server: {server}
Port: {port}
Secret: {secret}"""

    tg_link = f"tg://proxy?server={server}&port={port}&secret={secret}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Connect Proxy", url=tg_link)]
    ])

    sent = bot.send_message(
        chat_id=CHANNEL_ID,
        text=message,
        reply_markup=keyboard
    )

    posted.add(key)

    # Save message id + timestamp (optional tracking)
    with open("messages.txt", "a") as f:
        f.write(f"{sent.message_id}|{int(time.time())}\n")

# Save updated posted list
with open("posted.txt", "w") as f:
    f.write("\n".join(posted))
