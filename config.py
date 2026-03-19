# ============================================================
#  ✏️  FILL IN YOUR DETAILS HERE — this is the only file
#     you need to edit before running the bot
# ============================================================

# 1. Get this from @BotFather on Telegram → /newbot
BOT_TOKEN = "8633401654:AAFgBoHYSYc5n3hNUT0U67-OtL0Qdr_S6oo"

# 2. Your TON wallet address (open Tonkeeper → copy the address starting with UQ...)
HOT_WALLET_ADDRESS = "UQBiziX6rkVbYt9u2wDlW75tIaAhT3300UeyFbzYfZtZMKOq"  # ← paste your address here

# 3. Network: False = testnet (safe for testing), True = mainnet (real TON)
#    Get FREE testnet TON at: https://t.me/testgiver_ton_bot
TON_MAINNET = True

# 4. Optional — get a free API key at https://toncenter.com to avoid rate limits
TON_API_KEY = "640b4486094ffd81a5e49a4bb7c599fb55e8bfa3d391f140fb02b12b10c032ca"

# ============================================================
#  ⚙️  Advanced settings (you can leave these as-is)
# ============================================================

# How often (seconds) to check blockchain for new payments
POLL_INTERVAL_SECONDS = 15

# How long (minutes) to wait for a payment before timing out
PAYMENT_TIMEOUT_MINUTES = 10

# TON Center API endpoint (auto-selected based on TON_MAINNET)
TON_API_URL = (
    "https://toncenter.com/api/v2"
    if TON_MAINNET
    else "https://testnet.toncenter.com/api/v2"
)
