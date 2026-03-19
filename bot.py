"""
🎁 Telegram Gift Bot — Python version
======================================
Pay with TON crypto. Send gifts to yourself or others.

Run:  python bot.py
"""

import logging
import threading
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

import config
from gifts import GIFTS, get_all_categories, get_gifts_by_category, get_gift_by_id, cat_emoji
from ton_payment import create_payment_info, watch_payment, start_poller

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Bot init ───────────────────────────────────────────────────────────────────
bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="Markdown")

# ── Per-user state ─────────────────────────────────────────────────────────────
# { chat_id: { selected_gift, recipient, awaiting_recipient, orders, cancel_payment } }
user_state = {}
state_lock = threading.Lock()

def get_state(chat_id):
    with state_lock:
        return user_state.setdefault(chat_id, {})

def set_state(chat_id, **kwargs):
    with state_lock:
        user_state.setdefault(chat_id, {}).update(kwargs)

def clear_state(chat_id):
    with state_lock:
        user_state[chat_id] = {}


# ══════════════════════════════════════════════════════════════════════════════
#  Keyboard builders
# ══════════════════════════════════════════════════════════════════════════════

def kb(*rows):
    """Quick inline keyboard builder. Pass lists of (text, callback_data) tuples."""
    m = InlineKeyboardMarkup()
    for row in rows:
        m.row(*[InlineKeyboardButton(t, callback_data=d) for t, d in row])
    return m

def url_kb(label, url, cancel_data):
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton(label, url=url))
    m.row(InlineKeyboardButton("❌ Cancel", callback_data=cancel_data))
    return m


# ══════════════════════════════════════════════════════════════════════════════
#  Menus
# ══════════════════════════════════════════════════════════════════════════════

def send_main_menu(chat_id, name=""):
    greeting = f", {name}" if name else ""
    bot.send_message(
        chat_id,
        f"💎 *Welcome{greeting}!*\n\n"
        "Browse festival & event gifts, pay with *TON crypto*, and send them instantly!\n\n"
        "_Payments are verified on the TON blockchain — secure & trustless._",
        reply_markup=kb(
            [("🛍️ Browse All Gifts",   "browse_all")],
            [("🎊 Browse by Festival", "browse_events")],
            [("📋 My Orders",           "my_orders")],
            [("ℹ️ How It Works",        "how_it_works")],
        ),
    )


def send_gift_list(chat_id, gift_list, title):
    if not gift_list:
        bot.send_message(
            chat_id, "😕 No gifts in this category.",
            reply_markup=kb([("🏠 Main Menu", "main_menu")]),
        )
        return

    m = InlineKeyboardMarkup()
    for g in gift_list:
        m.row(InlineKeyboardButton(
            f"{g['emoji']} {g['name']} — 💎 {g['ton']} TON",
            callback_data=f"gift_{g['id']}",
        ))
    m.row(InlineKeyboardButton("🏠 Back to Menu", callback_data="main_menu"))

    bot.send_message(chat_id, title, reply_markup=m)


# ══════════════════════════════════════════════════════════════════════════════
#  /start command
# ══════════════════════════════════════════════════════════════════════════════

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    clear_state(msg.chat.id)
    send_main_menu(msg.chat.id, msg.from_user.first_name)


@bot.message_handler(commands=["wallet"])
def cmd_wallet(msg):
    try:
        from ton_payment import get_hot_wallet_address
        addr = get_hot_wallet_address()
        bot.send_message(
            msg.chat.id,
            f"💎 *Bot HOT Wallet:*\n`{addr}`\n\n"
            "_All TON payments arrive here. Bot detects them automatically._",
        )
    except RuntimeError as e:
        bot.send_message(msg.chat.id, f"❌ Wallet not configured:\n`{e}`")


# ══════════════════════════════════════════════════════════════════════════════
#  Callback query handler
# ══════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    msg_id  = call.message.message_id
    data    = call.data
    bot.answer_callback_query(call.id)

    # ── How it works ──────────────────────────────────────────────────────────
    if data == "how_it_works":
        bot.send_message(
            chat_id,
            "ℹ️ *How It Works*\n\n"
            "1️⃣ Browse gifts by festival or category\n"
            "2️⃣ Select a gift\n"
            "3️⃣ Choose: send to *yourself* or *another user*\n"
            "4️⃣ Bot gives you a wallet address + unique *memo code*\n"
            "5️⃣ Send TON from Tonkeeper / @wallet — *include the memo!*\n"
            "6️⃣ Bot confirms payment on-chain in ~15 seconds\n"
            "7️⃣ 🎁 Gift delivered!\n\n"
            "💡 *Get TON:* Open @wallet in Telegram or use Tonkeeper",
            reply_markup=kb([("🏠 Back", "main_menu")]),
        )

    # ── Main menu ─────────────────────────────────────────────────────────────
    elif data == "main_menu":
        clear_state(chat_id)
        send_main_menu(chat_id, call.from_user.first_name)

    # ── Browse events ─────────────────────────────────────────────────────────
    elif data == "browse_events":
        cats = get_all_categories()
        m = InlineKeyboardMarkup()
        for c in cats:
            m.row(InlineKeyboardButton(f"{cat_emoji(c)} {c}", callback_data=f"cat_{c}"))
        m.row(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
        bot.send_message(chat_id, "🎊 *Select a Festival or Event:*", reply_markup=m)

    # ── Browse all ────────────────────────────────────────────────────────────
    elif data == "browse_all":
        send_gift_list(chat_id, GIFTS, "🛍️ *All Available Gifts:*")

    # ── Browse by category ────────────────────────────────────────────────────
    elif data.startswith("cat_"):
        cat = data[4:]
        send_gift_list(chat_id, get_gifts_by_category(cat), f"{cat_emoji(cat)} *{cat} Gifts:*")

    # ── Gift detail ───────────────────────────────────────────────────────────
    elif data.startswith("gift_"):
        gift = get_gift_by_id(data[5:])
        if not gift:
            bot.send_message(chat_id, "❌ Gift not found.")
            return
        set_state(chat_id, selected_gift=gift)
        bot.send_message(
            chat_id,
            f"{gift['emoji']} *{gift['name']}*\n\n"
            f"📦 *Festival:* {gift['category']}\n"
            f"💎 *Price:* {gift['ton']} TON\n"
            f"🆔 *Gift ID:* `{gift['id']}`\n\n"
            f"📝 {gift['description']}\n\n"
            "*Who should receive this gift?*",
            reply_markup=kb(
                [("🎁 Send to Myself",       "recv_self")],
                [("👤 Send to Another User", "recv_other")],
                [("⬅️ Back to Gifts",        "browse_all")],
            ),
        )

    # ── Recipient: self ───────────────────────────────────────────────────────
    elif data == "recv_self":
        state = get_state(chat_id)
        gift = state.get("selected_gift")
        if not gift:
            bot.send_message(chat_id, "❌ No gift selected. Please start over.")
            return
        set_state(chat_id, recipient={
            "id": chat_id,
            "name": call.from_user.first_name,
            "is_self": True,
        })
        initiate_payment(chat_id, gift, call.from_user.first_name)

    # ── Recipient: other ──────────────────────────────────────────────────────
    elif data == "recv_other":
        set_state(chat_id, awaiting_recipient=True)
        bot.send_message(
            chat_id,
            "👤 *Who do you want to gift?*\n\n"
            "• *Forward* any message from that person here\n"
            "• Or type their *@username*\n\n"
            "_They must have started this bot to receive the notification._",
            reply_markup=kb([("❌ Cancel", "main_menu")]),
        )

    # ── Cancel payment ────────────────────────────────────────────────────────
    elif data.startswith("cancel_pay_"):
        state = get_state(chat_id)
        cancel_fn = state.get("cancel_payment")
        if cancel_fn:
            cancel_fn()
        set_state(chat_id, cancel_payment=None)
        bot.send_message(
            chat_id, "❌ Payment cancelled.",
            reply_markup=kb([("🏠 Main Menu", "main_menu")]),
        )

    # ── My orders ─────────────────────────────────────────────────────────────
    elif data == "my_orders":
        orders = get_state(chat_id).get("orders", [])
        if not orders:
            bot.send_message(
                chat_id,
                "📭 *No orders yet!*\n\nBrowse gifts to make your first purchase.",
                reply_markup=kb(
                    [("🛍️ Browse Gifts", "browse_all")],
                    [("🏠 Main Menu",    "main_menu")],
                ),
            )
        else:
            text = "📋 *Your Recent Orders:*\n\n"
            for i, o in enumerate(reversed(orders[-5:]), 1):
                text += f"{i}. {o['gift_emoji']} *{o['gift_name']}* → {o['recipient_name']}\n"
                text += f"   💎 {o['ton']} TON · {o['date']}\n"
                if o.get("tx_id"):
                    text += f"   🔗 `{o['tx_id'][:20]}...`\n"
                text += "\n"
            bot.send_message(chat_id, text,
                             reply_markup=kb([("🏠 Main Menu", "main_menu")]))


# ══════════════════════════════════════════════════════════════════════════════
#  Text messages — handle @username / forwarded message for recipient
# ══════════════════════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: not m.text or not m.text.startswith("/"))
def handle_text(msg):
    chat_id = msg.chat.id
    state   = get_state(chat_id)

    if not state.get("awaiting_recipient"):
        return  # not waiting for anything

    recipient_name = None
    recipient_id   = None

    if msg.forward_from:
        recipient_id   = msg.forward_from.id
        recipient_name = msg.forward_from.first_name
        if msg.forward_from.last_name:
            recipient_name += f" {msg.forward_from.last_name}"

    elif msg.text and msg.text.strip().startswith("@"):
        recipient_name = msg.text.strip()
        recipient_id   = None  # can't resolve @username to ID via basic Bot API

    else:
        bot.send_message(
            chat_id,
            "⚠️ Please *forward* a message from the recipient, or type their *@username*.",
            reply_markup=kb([("❌ Cancel", "main_menu")]),
        )
        return

    set_state(chat_id,
              awaiting_recipient=False,
              recipient={"id": recipient_id, "name": recipient_name, "is_self": False})

    gift = state.get("selected_gift")
    if not gift:
        bot.send_message(chat_id, "❌ No gift selected. Please start over.")
        return

    initiate_payment(chat_id, gift, recipient_name)


# ══════════════════════════════════════════════════════════════════════════════
#  TON payment flow
# ══════════════════════════════════════════════════════════════════════════════

def initiate_payment(chat_id, gift, recipient_name):
    try:
        pay_info = create_payment_info(gift["ton"])
    except RuntimeError as e:
        bot.send_message(
            chat_id,
            f"❌ Could not create payment.\n\n`{e}`\n\n"
            "Make sure `TON_WALLET_MNEMONIC` is set correctly in config.py",
        )
        return

    address    = pay_info["address"]
    memo       = pay_info["memo"]
    amount_ton = pay_info["amount_ton"]
    amount_nano= pay_info["amount_nano"]
    deep_link  = pay_info["deep_link"]
    payment_id = pay_info["payment_id"]

    # Send payment instructions
    pay_msg = bot.send_message(
        chat_id,
        f"💎 *Pay with TON*\n\n"
        f"🎁 *Gift:* {gift['emoji']} {gift['name']}\n"
        f"👤 *To:* {recipient_name}\n"
        f"💰 *Amount:* `{amount_ton} TON`\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📬 *Send TON to:*\n`{address}`\n\n"
        f"🔑 *Memo / Comment (required):*\n`{memo}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ _Always include the memo — it links your payment to this order!_\n\n"
        f"⏳ Waiting for blockchain confirmation... *({config.PAYMENT_TIMEOUT_MINUTES} min timeout)*",
        reply_markup=url_kb("💎 Open in TON Wallet", deep_link, f"cancel_pay_{payment_id}"),
    )

    # ── Callbacks ──────────────────────────────────────────────────────────────

    def on_confirmed(received_nano, tx_id):
        set_state(chat_id, cancel_payment=None)

        # Save order
        import datetime
        state  = get_state(chat_id)
        orders = state.get("orders", [])
        orders.append({
            "gift_id":        gift["id"],
            "gift_name":      gift["name"],
            "gift_emoji":     gift["emoji"],
            "ton":            amount_ton,
            "recipient_name": recipient_name,
            "date":           datetime.date.today().strftime("%d %b %Y"),
            "tx_id":          tx_id,
        })
        set_state(chat_id, orders=orders, selected_gift=None, recipient=None)

        # Edit the waiting message
        try:
            bot.edit_message_text(
                f"✅ *Payment Confirmed on TON Blockchain!*\n\n"
                f"{gift['emoji']} *{gift['name']}* → *{recipient_name}*\n"
                f"💎 {amount_ton} TON received\n"
                + (f"🔗 TX: `{tx_id[:24]}...`" if tx_id else ""),
                chat_id=chat_id,
                message_id=pay_msg.message_id,
            )
        except Exception:
            pass

        # Confirmation
        bot.send_message(
            chat_id,
            f"🎉 *Gift Sent Successfully!*\n\n"
            f"{gift['emoji']} *{gift['name']}* has been delivered to *{recipient_name}*!",
            reply_markup=kb(
                [("🛍️ Send Another Gift", "browse_all")],
                [("🏠 Main Menu",          "main_menu")],
            ),
        )

        # Notify recipient
        recipient = state.get("recipient") or {}
        r_id = recipient.get("id")
        if r_id and r_id != chat_id:
            try:
                bot.send_message(
                    r_id,
                    f"🎁 *You received a gift!*\n\n"
                    f"{gift['emoji']} *{gift['name']}* was gifted to you!\n\n"
                    "_Check your Telegram profile to see it._",
                )
            except Exception:
                pass

        # Telegram sendGift Bot API (Bot API 9.0+)
        _send_telegram_gift(chat_id, gift, recipient)

    def on_timeout():
        set_state(chat_id, cancel_payment=None)
        try:
            bot.edit_message_text(
                f"⏰ *Payment Timed Out*\n\n"
                f"No payment with memo `{memo}` received in "
                f"{config.PAYMENT_TIMEOUT_MINUTES} minutes.\n\n"
                "_Already sent TON? Contact support with your TX hash._",
                chat_id=chat_id,
                message_id=pay_msg.message_id,
                reply_markup=kb([("🔄 Try Again", f"gift_{gift['id']}")]),
            )
        except Exception:
            pass

    cancel_fn = watch_payment(
        payment_id, amount_nano,
        on_confirmed, on_timeout,
    )
    set_state(chat_id, cancel_payment=cancel_fn)


def _send_telegram_gift(buyer_chat_id, gift, recipient):
    """Call Telegram sendGift Bot API (requires Bot API 9.0+)."""
    target_id = recipient.get("id") if (recipient and not recipient.get("is_self")) else buyer_chat_id
    if not target_id:
        target_id = buyer_chat_id
    try:
        bot.send_gift(target_id, gift["id"])
        logger.info(f"🎁 Telegram gift {gift['id']} sent to {target_id}")
    except Exception as e:
        logger.warning(f"sendGift API failed (needs Bot API 9.0+): {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    network = "MAINNET ✅" if config.TON_MAINNET else "TESTNET 🧪"
    print(f"🤖 Telegram Gift Bot (Python) is starting...")
    print(f"💎 Network: {network}")
    print("Press Ctrl+C to stop.\n")

    start_poller()

    bot.infinity_polling(logger_level=logging.WARNING)
