# ============================================================
#  🎁  GIFT CATALOGUE
#
#  Each gift has:
#    id          - Telegram Gift ID  ← get real ones by running fetch_gifts.py
#    name        - Display name shown to users
#    emoji       - Decorative emoji
#    category    - Festival / event name
#    ton         - Price in TON (set your own rates)
#    description - Short description shown to users
# ============================================================

GIFTS = [
    # ── New Year ─────────────────────────────────────────────────────────────
    {"id": "5170233102089322756", "name": "Firework Bouquet",  "emoji": "🎆", "category": "New Year",  "ton": 0.5,  "description": "Ring in the New Year with a dazzling firework bouquet!"},
    {"id": "5170233102089322757", "name": "Golden Countdown",  "emoji": "🥂", "category": "New Year",  "ton": 1.0,  "description": "A glamorous golden toast to welcome the New Year."},
    {"id": "5170233102089322758", "name": "Midnight Star",     "emoji": "⭐", "category": "New Year",  "ton": 0.75, "description": "Wish upon a star as the clock strikes midnight."},

    # ── Christmas ─────────────────────────────────────────────────────────────
    {"id": "5170233102089322760", "name": "Christmas Tree",    "emoji": "🎄", "category": "Christmas", "ton": 1.0,  "description": "A sparkling Christmas tree to spread holiday cheer!"},
    {"id": "5170233102089322761", "name": "Santa's Gift Box",  "emoji": "🎁", "category": "Christmas", "ton": 1.5,  "description": "Ho ho ho! A special gift from Santa's sleigh."},
    {"id": "5170233102089322762", "name": "Snowflake",         "emoji": "❄️", "category": "Christmas", "ton": 0.5,  "description": "A unique snowflake — just like you!"},

    # ── Diwali ────────────────────────────────────────────────────────────────
    {"id": "5170233102089322770", "name": "Diya Lamp",         "emoji": "🪔", "category": "Diwali",    "ton": 0.5,  "description": "Light up someone's life with a traditional Diya this Diwali!"},
    {"id": "5170233102089322771", "name": "Sparkle Cracker",   "emoji": "✨", "category": "Diwali",    "ton": 0.75, "description": "Celebrate the festival of lights with golden sparkles."},
    {"id": "5170233102089322772", "name": "Sweet Box",         "emoji": "🍬", "category": "Diwali",    "ton": 1.0,  "description": "Share the sweetness of Diwali with a virtual mithai box."},

    # ── Valentine's Day ───────────────────────────────────────────────────────
    {"id": "5170233102089322780", "name": "Heart Bouquet",     "emoji": "💐", "category": "Valentine", "ton": 1.0,  "description": "Send your love with a gorgeous heart bouquet."},
    {"id": "5170233102089322781", "name": "Red Rose",          "emoji": "🌹", "category": "Valentine", "ton": 0.5,  "description": "A classic red rose — timeless symbol of love."},
    {"id": "5170233102089322782", "name": "Love Letter",       "emoji": "💌", "category": "Valentine", "ton": 0.75, "description": "Express your feelings with a heartfelt love letter."},

    # ── Eid ───────────────────────────────────────────────────────────────────
    {"id": "5170233102089322790", "name": "Crescent Moon",     "emoji": "🌙", "category": "Eid",       "ton": 0.75, "description": "Eid Mubarak! Share the joy of the crescent moon."},
    {"id": "5170233102089322791", "name": "Lantern",           "emoji": "🏮", "category": "Eid",       "ton": 1.0,  "description": "A glowing lantern to illuminate Eid celebrations."},

    # ── Birthday ──────────────────────────────────────────────────────────────
    {"id": "5170233102089322800", "name": "Birthday Cake",     "emoji": "🎂", "category": "Birthday",  "ton": 1.0,  "description": "Make someone's birthday extra special with a cake!"},
    {"id": "5170233102089322801", "name": "Party Popper",      "emoji": "🎉", "category": "Birthday",  "ton": 0.5,  "description": "Pop the confetti and celebrate their special day!"},
    {"id": "5170233102089322802", "name": "Gift Balloon",      "emoji": "🎈", "category": "Birthday",  "ton": 0.75, "description": "A colorful balloon bouquet for birthday celebrations."},

    # ── Holi ──────────────────────────────────────────────────────────────────
    {"id": "5170233102089322810", "name": "Color Splash",      "emoji": "🎨", "category": "Holi",      "ton": 0.5,  "description": "Throw vibrant colors and celebrate Holi!"},
    {"id": "5170233102089322811", "name": "Pichkari",          "emoji": "💦", "category": "Holi",      "ton": 0.75, "description": "Drench your friends in colors with a festive pichkari!"},

    # ── Halloween ─────────────────────────────────────────────────────────────
    {"id": "5170233102089322820", "name": "Pumpkin Lantern",   "emoji": "🎃", "category": "Halloween", "ton": 0.75, "description": "Trick or treat! A spooky pumpkin for Halloween."},
    {"id": "5170233102089322821", "name": "Ghost",             "emoji": "👻", "category": "Halloween", "ton": 0.5,  "description": "A friendly ghost to haunt your Halloween!"},
]

# ── Helper functions ──────────────────────────────────────────────────────────

def get_all_categories():
    """Return unique list of categories in order."""
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
    "New Year":  "🎆",
    "Christmas": "🎄",
    "Diwali":    "🪔",
    "Valentine": "💝",
    "Eid":       "🌙",
    "Birthday":  "🎂",
    "Holi":      "🎨",
    "Halloween": "🎃",
    "Easter":    "🐣",
}

def cat_emoji(category):
    return CATEGORY_EMOJIS.get(category, "🎊")
