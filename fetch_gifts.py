"""
🔍 Fetch Available Gifts from Telegram API
==========================================
Run this to get the real gift IDs you need to put in gifts.py:

    python fetch_gifts.py

It will print all current gifts with their IDs, emojis, and Star prices.
"""

import requests
import json
import config

def fetch_gifts():
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/getAvailableGifts"

    print(f"\n🔍 Fetching gifts from Telegram API...")
    print(f"   Token: {config.BOT_TOKEN[:10]}...\n")

    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return

    if not data.get("ok"):
        print(f"❌ Telegram API error: {data.get('description')}")
        print("   Make sure BOT_TOKEN in config.py is correct.")
        return

    gifts = data["result"]["gifts"]
    print(f"✅ Found {len(gifts)} available gifts:\n")
    print("─" * 60)

    for i, gift in enumerate(gifts, 1):
        sticker = gift.get("sticker", {})
        print(f"\n[{i}] Gift ID    : {gift['id']}")
        print(f"    Emoji      : {sticker.get('emoji', 'N/A')}")
        print(f"    Stars      : {gift['star_count']}")
        print(f"    Total      : {gift.get('total_count', 'unlimited')}")
        print(f"    Remaining  : {gift.get('remaining_count', 'unlimited')}")

    print("\n" + "─" * 60)
    print("\n📋 Copy these IDs into gifts.py — replace the placeholder `id` values!\n")

    # Also print as a handy Python list
    print("📦 Quick-copy format:\n")
    for gift in gifts:
        sticker = gift.get("sticker", {})
        emoji = sticker.get("emoji", "🎁")
        stars = gift["star_count"]
        ton_equiv = round(stars * 0.01, 2)  # rough estimate: 1 Star ≈ 0.01 TON
        print(f'  # {emoji}  Stars: {stars}  (~{ton_equiv} TON suggested)')
        print(f'  "{gift["id"]}",')
        print()

if __name__ == "__main__":
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Please set BOT_TOKEN in config.py first!")
    else:
        fetch_gifts()
