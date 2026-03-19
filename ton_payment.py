"""
TON Payment Monitor
===================
- Each order gets a unique 6-digit memo code
- User sends TON to the bot's hot wallet with this code as the transfer comment
- This module polls TON Center API every N seconds
- When a matching payment arrives → calls your on_confirmed callback
"""

import time
import random
import threading
import requests
import logging

import config

logger = logging.getLogger(__name__)

# ── Pending orders ─────────────────────────────────────────────────────────────
# Structure: { memo: { amount_nano, on_confirmed, on_timeout, timer } }
_pending = {}
_pending_lock = threading.Lock()

# ── Last seen transaction logical time (avoids re-processing old txs) ─────────
_last_lt = None

# ── Hot wallet address cache ───────────────────────────────────────────────────
_hot_wallet_address = None


# ══════════════════════════════════════════════════════════════════════════════
#  Wallet helpers
# ══════════════════════════════════════════════════════════════════════════════

def get_hot_wallet_address():
    """
    Derive the hot wallet address from the mnemonic in config.py.
    Uses tonsdk if installed, otherwise falls back to TON Center API lookup.
    Returns address string or raises RuntimeError.
    """
    global _hot_wallet_address
    if _hot_wallet_address:
        return _hot_wallet_address

    mnemonic = config.TON_WALLET_MNEMONIC.strip()
    if not mnemonic or mnemonic.startswith("word1"):
        raise RuntimeError(
            "TON_WALLET_MNEMONIC is not set in config.py!\n"
            "Generate a wallet at https://tonkeeper.com and paste the 24 words."
        )

    try:
        from tonsdk.crypto import mnemonic_to_wallet_key
        from tonsdk.contract.wallet import WalletVersionEnum, Wallets

        _pub, _priv = mnemonic_to_wallet_key(mnemonic.split())
        _wallet, _, _, addr = Wallets.from_mnemonics(
            mnemonic.split(), WalletVersionEnum.v4r2, workchain=0
        )
        _hot_wallet_address = addr.to_string(True, True, False)
        logger.info(f"Hot wallet: {_hot_wallet_address}")
        return _hot_wallet_address

    except ImportError:
        raise RuntimeError(
            "tonsdk not installed. Run:  pip install tonsdk\n"
            "Or manually paste your wallet address as HOT_WALLET_ADDRESS in config.py"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Payment request creation
# ══════════════════════════════════════════════════════════════════════════════

def ton_to_nano(ton: float) -> int:
    return int(ton * 1_000_000_000)

def nano_to_ton(nano: int) -> float:
    return nano / 1_000_000_000


def create_payment_info(amount_ton: float) -> dict:
    """
    Generate payment details for a new order.

    Returns dict:
        address     - wallet address to send TON to
        memo        - 6-digit unique code (must be included as transfer comment)
        amount_ton  - price in TON
        amount_nano - price in nanoTON
        deep_link   - ton:// link that opens Tonkeeper/wallet
        payment_id  - same as memo (used as key)
    """
    address = get_hot_wallet_address()
    memo = str(random.randint(100_000, 999_999))
    amount_nano = ton_to_nano(amount_ton)
    deep_link = (
        f"ton://transfer/{address}"
        f"?amount={amount_nano}"
        f"&text={memo}"
    )
    return {
        "address":    address,
        "memo":       memo,
        "amount_ton": amount_ton,
        "amount_nano": amount_nano,
        "deep_link":  deep_link,
        "payment_id": memo,
    }


def watch_payment(payment_id: str, amount_nano: int,
                  on_confirmed, on_timeout,
                  timeout_minutes: int = None):
    """
    Register callbacks for a payment.

    on_confirmed(received_nano, tx_id) — called when payment detected
    on_timeout()                        — called if timeout expires

    Returns a cancel() function you can call to abort watching.
    """
    timeout_sec = (timeout_minutes or config.PAYMENT_TIMEOUT_MINUTES) * 60

    def _timeout_handler():
        with _pending_lock:
            if payment_id in _pending:
                del _pending[payment_id]
        logger.info(f"Payment {payment_id} timed out")
        on_timeout()

    timer = threading.Timer(timeout_sec, _timeout_handler)
    timer.daemon = True
    timer.start()

    with _pending_lock:
        _pending[payment_id] = {
            "amount_nano": amount_nano,
            "on_confirmed": on_confirmed,
            "on_timeout": on_timeout,
            "timer": timer,
        }

    def cancel():
        with _pending_lock:
            entry = _pending.pop(payment_id, None)
        if entry:
            entry["timer"].cancel()

    return cancel


# ══════════════════════════════════════════════════════════════════════════════
#  Blockchain poller
# ══════════════════════════════════════════════════════════════════════════════

def _poll_once():
    global _last_lt

    with _pending_lock:
        if not _pending:
            return

    try:
        address = get_hot_wallet_address()
    except RuntimeError as e:
        logger.error(str(e))
        return

    headers = {}
    if config.TON_API_KEY:
        headers["X-API-Key"] = config.TON_API_KEY

    params = {"address": address, "limit": 20}
    if _last_lt:
        params["lt"] = _last_lt

    try:
        resp = requests.get(
            f"{config.TON_API_URL}/getTransactions",
            params=params,
            headers=headers,
            timeout=10,
        )
        data = resp.json()
    except Exception as e:
        logger.warning(f"TON poll request failed: {e}")
        return

    if not data.get("ok") or not data.get("result"):
        return

    txs = data["result"]

    # Update pointer so we don't re-process
    if txs and txs[0].get("transaction_id", {}).get("lt"):
        _last_lt = txs[0]["transaction_id"]["lt"]

    for tx in txs:
        in_msg = tx.get("in_msg", {})
        if not in_msg or not in_msg.get("value") or in_msg["value"] == "0":
            continue

        memo = (in_msg.get("message") or "").strip()
        incoming_nano = int(in_msg["value"])

        with _pending_lock:
            order = _pending.get(memo)

        if not order:
            continue

        # Allow ±1% tolerance on amount
        expected = order["amount_nano"]
        tolerance = max(expected // 100, 1)
        if incoming_nano < expected - tolerance:
            logger.warning(
                f"Payment {memo}: got {nano_to_ton(incoming_nano):.4f} TON, "
                f"expected {nano_to_ton(expected):.4f} TON — too low"
            )
            continue

        tx_id = tx.get("transaction_id", {}).get("hash", "")
        logger.info(f"✅ Payment confirmed: memo={memo}, amount={nano_to_ton(incoming_nano):.4f} TON")

        with _pending_lock:
            entry = _pending.pop(memo, None)

        if entry:
            entry["timer"].cancel()
            # Call confirmed callback in a new thread so polling isn't blocked
            threading.Thread(
                target=entry["on_confirmed"],
                args=(incoming_nano, tx_id),
                daemon=True,
            ).start()


def start_poller():
    """Start the background blockchain polling thread."""
    network = "MAINNET" if config.TON_MAINNET else "TESTNET"
    logger.info(f"💎 TON payment poller started ({network}, every {config.POLL_INTERVAL_SECONDS}s)")

    def _loop():
        while True:
            try:
                _poll_once()
            except Exception as e:
                logger.error(f"Poller error: {e}")
            time.sleep(config.POLL_INTERVAL_SECONDS)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
