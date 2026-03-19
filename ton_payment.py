"""
TON Payment Monitor
===================
- Each order gets a unique 6-digit memo code
- User sends TON to the bot's hot wallet with this memo as transfer comment
- Polls TON Center API every N seconds and matches by memo + amount
"""

import time
import random
import threading
import requests
import logging

import config

logger = logging.getLogger(__name__)

_pending       = {}        # { memo: { amount_nano, on_confirmed, on_timeout, timer } }
_pending_lock  = threading.Lock()
_seen_hashes   = set()     # already-processed tx hashes
_hot_wallet    = None


# ══════════════════════════════════════════════════════════════════════════════
#  Wallet address
# ══════════════════════════════════════════════════════════════════════════════

def get_hot_wallet_address():
    global _hot_wallet
    if _hot_wallet:
        return _hot_wallet
    address = getattr(config, "HOT_WALLET_ADDRESS", "").strip()
    if not address or "..." in address:
        raise RuntimeError(
            "HOT_WALLET_ADDRESS is not set in config.py!\n"
            "Open Tonkeeper → copy your wallet address → paste it into config.py"
        )
    _hot_wallet = address
    print(f"💎 Hot wallet: {_hot_wallet}")
    return _hot_wallet


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def ton_to_nano(ton: float) -> int:
    return int(ton * 1_000_000_000)

def nano_to_ton(nano) -> float:
    return int(nano) / 1_000_000_000


# ══════════════════════════════════════════════════════════════════════════════
#  Create payment info
# ══════════════════════════════════════════════════════════════════════════════

def create_payment_info(amount_ton: float) -> dict:
    address    = get_hot_wallet_address()
    memo       = str(random.randint(100_000, 999_999))
    amount_nano = ton_to_nano(amount_ton)
    deep_link  = f"ton://transfer/{address}?amount={amount_nano}&text={memo}"
    print(f"📋 New order created | memo={memo} | amount={amount_ton} TON")
    return {
        "address":     address,
        "memo":        memo,
        "amount_ton":  amount_ton,
        "amount_nano": amount_nano,
        "deep_link":   deep_link,
        "payment_id":  memo,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Watch for payment
# ══════════════════════════════════════════════════════════════════════════════

def watch_payment(payment_id, amount_nano, on_confirmed, on_timeout, timeout_minutes=None):
    timeout_sec = (timeout_minutes or config.PAYMENT_TIMEOUT_MINUTES) * 60

    def _on_timeout():
        with _pending_lock:
            _pending.pop(payment_id, None)
        print(f"⏰ Payment timed out: memo={payment_id}")
        on_timeout()

    timer = threading.Timer(timeout_sec, _on_timeout)
    timer.daemon = True
    timer.start()

    with _pending_lock:
        _pending[payment_id] = {
            "amount_nano":  amount_nano,
            "on_confirmed": on_confirmed,
            "on_timeout":   on_timeout,
            "timer":        timer,
        }
    print(f"👀 Watching for payment | memo={payment_id} | expected={nano_to_ton(amount_nano):.4f} TON | timeout={timeout_sec//60}min")

    def cancel():
        with _pending_lock:
            entry = _pending.pop(payment_id, None)
        if entry:
            entry["timer"].cancel()
        print(f"❌ Payment watch cancelled: memo={payment_id}")

    return cancel


# ══════════════════════════════════════════════════════════════════════════════
#  Blockchain poller
# ══════════════════════════════════════════════════════════════════════════════

def _poll_once():
    with _pending_lock:
        if not _pending:
            return
        pending_snapshot = dict(_pending)

    try:
        address = get_hot_wallet_address()
    except RuntimeError as e:
        print(f"❌ Wallet error: {e}")
        return

    headers = {}
    if config.TON_API_KEY:
        headers["X-API-Key"] = config.TON_API_KEY

    try:
        resp = requests.get(
            f"{config.TON_API_URL}/getTransactions",
            params={"address": address, "limit": 20},
            headers=headers,
            timeout=15,
        )
        data = resp.json()
    except Exception as e:
        print(f"⚠️  TON API request failed: {e}")
        return

    if not data.get("ok"):
        print(f"⚠️  TON API error: {data.get('description', data)}")
        return

    txs = data.get("result", [])
    print(f"🔍 Polled | {len(txs)} txs | {len(pending_snapshot)} pending orders: {list(pending_snapshot.keys())}")

    for tx in txs:
        tx_id   = tx.get("transaction_id", {})
        tx_hash = tx_id.get("hash", "")

        if tx_hash in _seen_hashes:
            continue

        in_msg = tx.get("in_msg") or {}
        value  = in_msg.get("value", "0") or "0"

        if value == "0":
            # outgoing tx, skip
            _seen_hashes.add(tx_hash)
            continue

        incoming_nano = int(value)

        # memo can be in "message" or "msg_data" → "text"
        memo = (
            in_msg.get("message")
            or (in_msg.get("msg_data") or {}).get("text")
            or ""
        ).strip()

        print(
            f"   TX: {tx_hash[:16]}... | "
            f"{nano_to_ton(incoming_nano):.4f} TON | "
            f"memo='{memo}'"
        )

        _seen_hashes.add(tx_hash)

        if not memo:
            print(f"   ↳ No memo — skipping")
            continue

        order = pending_snapshot.get(memo)
        if not order:
            print(f"   ↳ Memo '{memo}' not in pending orders — skipping")
            continue

        # Amount check — 5% tolerance
        expected  = order["amount_nano"]
        tolerance = max(expected * 5 // 100, 1)
        if incoming_nano < expected - tolerance:
            print(
                f"   ↳ Amount too low: got {nano_to_ton(incoming_nano):.4f} TON, "
                f"expected {nano_to_ton(expected):.4f} TON — skipping"
            )
            continue

        # ✅ Confirmed!
        print(f"✅ PAYMENT CONFIRMED | memo={memo} | {nano_to_ton(incoming_nano):.4f} TON | tx={tx_hash[:16]}...")

        with _pending_lock:
            entry = _pending.pop(memo, None)

        if entry:
            entry["timer"].cancel()
            threading.Thread(
                target=entry["on_confirmed"],
                args=(incoming_nano, tx_hash),
                daemon=True,
            ).start()


# ══════════════════════════════════════════════════════════════════════════════
#  Start
# ══════════════════════════════════════════════════════════════════════════════

def start_poller():
    network = "MAINNET ✅" if config.TON_MAINNET else "TESTNET 🧪"
    print(f"💎 TON poller starting | {network} | every {config.POLL_INTERVAL_SECONDS}s")

    def _loop():
        while True:
            try:
                _poll_once()
            except Exception as e:
                print(f"❌ Poller crash: {e}")
            time.sleep(config.POLL_INTERVAL_SECONDS)

    t = threading.Thread(target=_loop, daemon=True)
    t.daemon = True
    t.start()
