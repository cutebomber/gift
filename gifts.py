# ============================================================
#  🎁  GIFT CATALOGUE — Real Telegram Gift IDs
#
#  Each gift has:
#    id          - Real Telegram Gift ID
#    name        - Display name shown to users
#    emoji       - Decorative emoji
#    category    - Festival / event name
#    ton         - Price in TON (set your own rates)
#    description - Short description shown to users
#
#  Add more gifts below as Telegram releases them!
# ============================================================

GIFTS = [
    {
        "id": "5893356958802511476",
        "name": "Green Bear",
        "emoji": "🐻",
        "category": "Special",
        "ton": 1.0,
        "description": "A cute green bear — a rare and unique Telegram gift!",
    },
    {
        "id": "5866352046986232958",
        "name": "Pink Bear",
        "emoji": "🐻",
        "category": "Special",
        "ton": 1.0,
        "description": "An adorable pink bear — send it to someone special!",
    },
    {
        "id": "5800655655995968830",
        "name": "White Bear",
        "emoji": "🐻",
        "category": "Special",
        "ton": 1.0,
        "description": "A soft white bear — a sweet gift for anyone you care about.",
    },
    {
        "id": "5956217000635139069",
        "name": "Christmas Bear",
        "emoji": "🎄",
        "category": "Christmas",
        "ton": 1.5,
        "description": "A festive Christmas bear — spread holiday cheer!",
    },
]

# ── Helper functions ──────────────────────────────────────────────────────────

def get_all_categories():
    seen = []
    for g in GIFTS:
        if g["category"] not in seen:
            seen.append(g["category"])
    return seen

def get_gifts_by_category(category):
    return [g for g in GIFTS if g["category"] == category]

def get_gift_by_id(gift_id):
    return next((g for g in GIFTS if g["id"] == gift_id), None)

CATEGORY_EMOJIS = {
    "Special":   "⭐",
    "Christmas": "🎄",
    "New Year":  "🎆",
    "Diwali":    "🪔",
    "Valentine": "💝",
    "Eid":       "🌙",
    "Birthday":  "🎂",
    "Holi":      "🎨",
    "Halloween": "🎃",
}

def cat_emoji(category):
    return CATEGORY_EMOJIS.get(category, "🎊")
