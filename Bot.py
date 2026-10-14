# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║     Kairozen All-in-One Bot v4 — カイロゼン                  ║
║     ហាង + SMM Panel · ដាក់លុយ KHQR · Top Up Game Menu       ║
║     Global Discount · Panel Admin · Promo Code              ║
║     Compatible: Python 3.10+ · Termux / Pydroid 3         ║
╚══════════════════════════════════════════════════════════════╝
ដំឡើង:
  pip install pyTelegramBotAPI requests flask qrcode pillow --break-system-packages
"""

import json, logging, time, re, threading, hashlib, io, os, sys, subprocess, datetime
import requests as http_req
import telebot
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from flask import Flask, request as flask_request, jsonify
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─── COLOR CONSTANTS FOR TERMINAL ───
CLR_RESET   = "\033[0m"
CLR_BOLD    = "\033[1m"
CLR_RED     = "\033[91m"
CLR_GREEN   = "\033[92m"
CLR_YELLOW  = "\033[93m"
CLR_BLUE    = "\033[94m"
CLR_MAGENTA = "\033[95m"
CLR_CYAN    = "\033[96m"
CLR_WHITE   = "\033[97m"

BG_RED      = "\033[41m"
BG_GREEN    = "\033[42m"
BG_BLUE     = "\033[44m"

# Custom Colored Formatter for Logging
class ColoredFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG:    f"{CLR_CYAN}%(asctime)s{CLR_RESET} [{CLR_BLUE}%(levelname)s{CLR_RESET}] %(message)s",
        logging.INFO:     f"{CLR_CYAN}%(asctime)s{CLR_RESET} [{CLR_GREEN}%(levelname)s{CLR_RESET}] %(message)s",
        logging.WARNING:  f"{CLR_CYAN}%(asctime)s{CLR_RESET} [{CLR_YELLOW}%(levelname)s{CLR_RESET}] %(message)s",
        logging.ERROR:    f"{CLR_CYAN}%(asctime)s{CLR_RESET} [{CLR_RED}%(levelname)s{CLR_RESET}] %(message)s",
        logging.CRITICAL: f"{CLR_CYAN}%(asctime)s{CLR_RESET} [{CLR_BOLD}{CLR_RED}%(levelname)s{CLR_RESET}] %(message)s"
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

# Setup Logging with Colors
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter())
logger.addHandler(console_handler)

# ─── Auto-install deps ───
def _ensure_deps():
    pkgs = {"PIL": "pillow", "qrcode": "qrcode"}
    for mod, pkg in pkgs.items():
        try: __import__(mod)
        except ImportError:
            logger.info(f"{CLR_YELLOW}Installing missing package: {pkg}...{CLR_RESET}")
            subprocess.run([sys.executable, "-m", "pip", "install", pkg,
                            "--break-system-packages", "-q"], check=False)
_ensure_deps()

import qrcode
from PIL import Image, ImageDraw, ImageFont

# ═══════════════════════════════════════════════════════════
#  CONFIG  — ដូរតម្លៃទាំងនេះ
# ═══════════════════════════════════════════════════════════
BOT_TOKEN          = "8809786210:AAFQ_MKyKF6hOOSoo9MhH7wrhCQKZCq1XKQ"
ADMIN_ID           = 5630396613

# Bakong KHQR (ដាក់ Token ពេញលេញពីអ៊ីមែលរបស់អ្នក)
BAKONG_TOKEN       = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXJjb2pMZm1lYzJNY1GQ2NDAyYiJvJiJvJjkuSWJXi03NDQzNDQzNTIzNzFNaHptNGxDbTYiLCJpc3MiOiJCYWtvbmcifQ.eyJhaGNvdW50X2lkIjoibW9uX3NhbW5hbmdAYmtydCIsImRhdGVfaXNzdWVkIjoiMTc2MzgyOTc1MCIsImV4cGlyZXNfYXQiOjE4MjkyMzg5NTB9"
BANK_ACCOUNT       = "mon_samnang@bkrt"
MERCHANT_NAME      = "Chet Sorithya"
MERCHANT_CITY      = "Phnom Penh"

DEPOSIT_EXPIRE_SEC = 300   # 5 នាទី
POLL_INTERVAL      = 5
STOCK_ALERT_MIN    = 5

# ═══════════════════════════════════════════════════════════
#  FILES
# ═══════════════════════════════════════════════════════════
WALLETS_FILE    = "aio_wallets.json"
USERS_FILE      = "aio_users.json"
LANG_FILE       = "aio_lang.json"
PROMO_FILE      = "aio_promos.json"
SETTINGS_FILE   = "aio_settings.json"
DISCOUNT_FILE   = "aio_discount.json"   # Global Discount File

PRODUCTS_FILE   = "aio_products.json"
ORDERS_FILE     = "aio_orders.json"
STOCK_FILE      = "aio_stock.json"
STORE_DEP_FILE  = "aio_store_deposits.json"
SEEN_TXN_FILE   = "aio_seen_txn.json"

SMM_API_FILE    = "aio_smm_api.json"
SMM_SVC_FILE    = "aio_smm_services.json"
SMM_ORD_FILE    = "aio_smm_orders.json"
SMM_PROFIT_FILE = "aio_smm_profit.json"
SMM_POLL_FILE   = "aio_smm_poll.json"
LIVECHAT_FILE   = "aio_livechat.json"     # Live Chat Mapping File

def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return default

def _save(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e: logger.error(f"{CLR_RED}Save {path}: {e}{CLR_RESET}")

# ─── Load all state ───
wallets         = _load(WALLETS_FILE,   {})
users_db        = _load(USERS_FILE,     {})
user_lang       = _load(LANG_FILE,      {})
promos          = _load(PROMO_FILE,     {})
settings        = _load(SETTINGS_FILE,  {})
discount_config = _load(DISCOUNT_FILE,  {"active": False, "pct": 0})

products        = _load(PRODUCTS_FILE,  [])
orders          = _load(ORDERS_FILE,    {})
stock           = _load(STOCK_FILE,     {})
store_deps      = _load(STORE_DEP_FILE, {})
seen_txn        = set(_load(SEEN_TXN_FILE, []))
livechat_sessions = _load(LIVECHAT_FILE, {}) # admin_msg_id -> user_uid

smm_api         = _load(SMM_API_FILE,   {"url": "", "key": ""})
smm_services    = _load(SMM_SVC_FILE,   {})
smm_orders      = _load(SMM_ORD_FILE,   {})
smm_profit      = _load(SMM_PROFIT_FILE,{"pct": 20})
smm_poll        = _load(SMM_POLL_FILE,  {"interval": POLL_INTERVAL})

waiting         = {}   # uid -> step/dict
lang_cooldown   = {}
livechat_users  = set() # uid set of users currently in live chat mode

# Default products including Mobile Legends, Free Fire KH/SG, Roblox, and PUBG Mobile
if not products:
    products = [
        {"id": "mobilelegends", "name": "Mobile Legends", "icon": "⚔️",
         "desc": "MLBB Top Up · Delivery via User ID & Zone ID",
         "plans": [
             {"label": "86 Diamonds", "price": 1.20},
             {"label": "172 Diamonds", "price": 2.40},
             {"label": "257 Diamonds", "price": 3.60},
             {"label": "706 Diamonds", "price": 9.50}
         ]},
        {"id": "freefire", "name": "Free Fire KH/SG", "icon": "💎",
         "desc": "Free Fire KH/SG Top Up · Delivery via User ID",
         "plans": [
             {"label": "Weekly Pass", "price": 1.54},
             {"label": "Monthly Membership", "price": 7.59},
             {"label": "Weekly Lite", "price": 0.31},
             {"label": "20 Diamonds", "price": 0.18},
             {"label": "40 Diamonds", "price": 0.36},
             {"label": "60 Diamonds", "price": 0.51},
             {"label": "100 Diamonds", "price": 0.87},
             {"label": "160 Diamonds", "price": 1.37},
             {"label": "205 Diamonds", "price": 1.75},
             {"label": "420 Diamonds", "price": 3.51},
             {"label": "650 Diamonds", "price": 5.39},
             {"label": "840 Diamonds", "price": 6.98},
             {"label": "1100 Diamonds", "price": 8.79},
             {"label": "2250 Diamonds", "price": 17.85},
             {"label": "3350 Diamonds", "price": 25.79},
             {"label": "4500 Diamonds", "price": 33.85},
             {"label": "4765 Diamonds", "price": 37.19},
             {"label": "5600 Diamonds", "price": 43.59},
             {"label": "6700 Diamonds", "price": 50.79},
             {"label": "7650 Diamonds", "price": 58.98},
             {"label": "11500 Diamonds", "price": 87.89}
         ]},
        {"id": "roblox", "name": "Roblox Robux", "icon": "🟥",
         "desc": "Roblox Robux Top Up · Delivery via Username",
         "plans": [
             {"label": "400 Robux", "price": 4.99},
             {"label": "800 Robux", "price": 9.99},
             {"label": "1700 Robux", "price": 19.99}
         ]},
        {"id": "pubgmobile", "name": "PUBG Mobile", "icon": "🔫",
         "desc": "PUBG Mobile UC Top Up · Delivery via Player ID",
         "plans": [
             {"label": "60 UC", "price": 0.99},
             {"label": "325 UC", "price": 4.99},
             {"label": "660 UC", "price": 9.99},
             {"label": "1800 UC", "price": 24.99}
         ]},
    ]
    _save(PRODUCTS_FILE, products)

# ═══════════════════════════════════════════════════════════
#  BOT + HTTP
# ═══════════════════════════════════════════════════════════
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

def _make_session():
    s = http_req.Session()
    r = Retry(total=3, backoff_factor=2, status_forcelist=[500,502,503,504])
    a = HTTPAdapter(max_retries=r)
    s.mount("http://", a); s.mount("https://", a)
    return s
http = _make_session()

# ═══════════════════════════════════════════════════════════
#  LANGUAGE
# ═══════════════════════════════════════════════════════════
STRINGS = {
    "kh": {
        "welcome": (
            "👋 សូស្ដីមក <b>Kairozen カイロゼン</b>!\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🌟 Bot នេះផ្ដល់សេវាកម្ម:\n"
            "🛍️ ទិញផលិតផលឌីជីថល & Top Up Game\n"
            "📊 សេវា SMM (Followers/Likes)\n"
            "💳 បញ្ចូលលុយ · ប្រវត្តិ · ជំនួយ\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💰 សាច់ប្រាក់: <b>${:.2f}</b>"
        ),
        "select_lang":   "🌐 ជ្រើសរើសភាសា:",
        "lang_set":      "✅ ភាសាត្រូវបានផ្លាស់ប្ដូរ!",
        "menu":          "🏠 ត្រឡប់ Menu ដើម",
        "banned":        "🚫 គណនីរបស់អ្នកត្រូវបាន ban!",
        "cancel_ok":     "🏠 Menu",
        "no_service":    "❌ គ្មាន SMM Service ទេ",
        "choose_platform": "ជ្រើស Platform:",
        "choose_qty":    "ជ្រើស ចំនួន:",
        "send_link":     "ផ្ញើ Link របស់អ្នក:",
        "low_balance":   "❌ លុយមិនគ្រប់!",
        "order_done":    "✅ បញ្ជាទិញបានជោគជ័យ!",
        "deposit_ok":    "✅ ដាក់លុយបានជោគជ័យ!",
        "qr_expired":    "⏰ QR ផុតកំណត់! សូម top up ម្ដងទៀត",
        "qr_error":      "⚠️ QR Generate Error! ទំនាក់ Admin",
        "order_notfound":"❌ Order រកមិនឃើញ!",
        "no_orders":     "❌ គ្មាន Order ទេ!",
        "how_to_use": (
            "💡 <b>របៀបប្រើប្រាស់</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ ចុច <b>💳 ដាក់ប្រាក់</b> → ជ្រើស ចំនួន → ស្កេន QR តាម Bakong\n"
            "2️⃣ ចុច <b>🛍️ ហាងឌីជីថល</b> → ជ្រើស ផលិតផល → Plan → ទូទាត់\n"
            "3️⃣ ចុច <b>💎 ថុបអាប់ហ្គេម</b> → ជ្រើសហ្គេម និងកញ្ចប់ → បញ្ចូល ID\n"
            "4️⃣ ចុច <b>📊 សេវាកម្ម SMM</b> → Platform → សេវា → ចំនួន → ផ្ញើ Link"
        ),
        "support_msg": (
            "💬 <b>ជំនួយ Support</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💬 រាល់បញ្ហា ឬក៏ចម្ងល់ផ្សេងៗ សូមទាក់ទងមកកាន់ Telegram ផ្ទាល់៖\n"
            "👉 <b>@ChetSorithya01</b>"
        ),
        "fallback": "❓ ប្រើ Menu ខាងក្រោម",
    },
    "en": {
        "welcome": (
            "👋 Welcome to <b>Kairozen カイロゼン</b>!\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🌟 Services available:\n"
            "🛍️ Buy Digital Products & Game Top Up\n"
            "📊 SMM Services (Followers/Likes)\n"
            "💳 Top Up · History · Support\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💰 Balance: <b>${:.2f}</b>"
        ),
        "select_lang":   "🌐 Select Language:",
        "lang_set":      "✅ Language changed!",
        "menu":          "🏠 Back to Menu",
        "banned":        "🚫 Your account has been banned!",
        "cancel_ok":     "🏠 Menu",
        "no_service":    "❌ No SMM Services available",
        "choose_platform": "Choose Platform:",
        "choose_qty":    "Choose Quantity:",
        "send_link":     "Send your Link:",
        "low_balance":   "❌ Insufficient balance!",
        "order_done":    "✅ Order placed successfully!",
        "deposit_ok":    "✅ Deposit successful!",
        "qr_expired":    "⏰ QR expired! Please top up again",
        "qr_error":      "⚠️ QR Generate Error! Contact Admin",
        "order_notfound":"❌ Order not found!",
        "no_orders":     "❌ No orders yet!",
        "how_to_use": (
            "💡 <b>How to Use</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ Tap <b>💳 Top Up</b> → Choose Amount → Scan Bakong QR\n"
            "2️⃣ Tap <b>🛍️ Shop</b> → Choose Product → Plan → Pay\n"
            "3️⃣ Tap <b>💎 Game Top Up</b> → Choose Game/Package → Enter ID\n"
            "4️⃣ Tap <b>📊 SMM Services</b> → Platform → Service → Qty → Send Link"
        ),
        "support_msg": (
            "💬 <b>Support</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💬 For any issues or questions, please contact via Telegram:\n"
            "👉 <b>@ChetSorithya01</b>"
        ),
        "fallback": "❓ Use the menu below",
    },
}

def get_lang(uid): return user_lang.get(str(uid), "kh")

def t(uid, key, *args):
    lang = get_lang(uid)
    s = STRINGS.get(lang, STRINGS["kh"]).get(key) or STRINGS["kh"].get(key, key)
    if args:
        try: return s.format(*args)
        except: return s
    return s

def toggle_lang(uid):
    uid_str = str(uid)
    now = time.time()
    if now - lang_cooldown.get(uid_str, 0) < 3.0: return
    lang_cooldown[uid_str] = now
    cycle = {"kh": "en", "en": "kh"}
    user_lang[uid_str] = cycle.get(get_lang(uid), "kh")
    _save(LANG_FILE, user_lang)

def lang_flag(uid):
    return {"kh": "🇰🇭 ខ្មែរ", "en": "🇬🇧 English"}.get(get_lang(uid), "🇰🇭")

# ═══════════════════════════════════════════════════════════
#  WALLET & DISCOUNT HELPERS
# ═══════════════════════════════════════════════════════════
def bal(uid): return float(wallets.get(str(uid), 0))
def add_bal(uid, amt):
    wallets[str(uid)] = round(bal(uid) + amt, 2)
    _save(WALLETS_FILE, wallets)
def ded_bal(uid, amt):
    wallets[str(uid)] = max(0, round(bal(uid) - amt, 2))
    _save(WALLETS_FILE, wallets)
def set_bal(uid, amt):
    wallets[str(uid)] = round(float(amt), 2)
    _save(WALLETS_FILE, wallets)

def _calc_discounted_price(price):
    if discount_config.get("active", False):
        pct = float(discount_config.get("pct", 0))
        return round(price * (1 - pct / 100), 2)
    return price

# ═══════════════════════════════════════════════════════════
#  PROMO CODE
# ═══════════════════════════════════════════════════════════
def apply_promo(uid, code, amount):
    code = code.strip().upper()
    p = promos.get(code)
    if not p: return amount, 0, "❌ Promo Code ខុស!"
    if p.get("uses", 0) > 0 and p.get("used", 0) >= p["uses"]:
        return amount, 0, "❌ Promo Code ផុតសិទ្ធហើយ!"
    user_used = p.get("user_used", {})
    if str(uid) in user_used:
        return amount, 0, "❌ អ្នកបានប្រើ Promo Code នេះហើយ!"
    if p.get("pct", False):
        discount = round(amount * float(p["discount"]) / 100, 2)
    else:
        discount = min(float(p["discount"]), amount)
    final = max(0, round(amount - discount, 2))
    return final, discount, None

def confirm_promo(code, uid):
    code = code.strip().upper()
    p = promos.get(code)
    if not p: return
    p["used"] = p.get("used", 0) + 1
    uu = p.get("user_used", {})
    uu[str(uid)] = 1
    p["user_used"] = uu
    _save(PROMO_FILE, promos)

# ═══════════════════════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════════════════════
def main_kb(uid=None):
    lang = get_lang(uid) if uid else "kh"
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("🛍️ Shop",          "💎 Game Top Up")
        kb.row("📊 SMM Services",  "📦 Orders")
        kb.row("💳 Top Up",        "👜 Wallet",         "📜 History")
        kb.row("💬 Support",       "💡 How to Use",    "🌐 Language")
    else:
        kb.row("🛍️ ហាងឌីជីថល",    "💎 ថុបអាប់ហ្គេម")
        kb.row("📊 សេវាកម្ម SMM",  "📦 ការបញ្ជាទិញ")
        kb.row("💳 ដាក់ប្រាក់",    "👜 កាបូបលុយ",      "📜 ប្រវត្តិ")
        kb.row("💬 ជំនួយ Support", "💡 របៀបប្រើប្រាស់", "🌐 ភាសា / Language")
    return kb

def admin_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🛍️ ផលិតផល",       "📦 ការបញ្ជាទិញ")
    kb.row("💎 គ្រប់គ្រងហ្គេម",   "✏️ កែតម្លៃហ្គេម")
    kb.row("📦 ស្តុក",         "➕ បន្ថែមស្តុក",    "➕ បន្ថែមផលិតផល")
    kb.row("➕ បន្ថែមគ្រប់សេវាកម្ម", "🔥 បញ្ចុះតម្លៃទាំងអស់")
    kb.row("✏️ កែតម្លៃ",       "💳 ប្រាក់បញ្ញើ")
    kb.row("━━━ 📊 SMM ━━━")
    kb.row("📊 ការបញ្ជា SMM",  "⚙️ កំណត់ SMM API")
    kb.row("➕ បន្ថែម SMM",    "🗑️ លុប SMM")
    kb.row("💹 ប្រាក់ចំណេញ SMM")
    kb.row("━━━ 💰 ហិរញ្ញវត្ថុ ━━━")
    kb.row("💰 កាបូបលុយ",      "💰 ឆែកលុយ API")
    kb.row("💸 បន្ថែមប្រាក់",   "💔 កាត់ប្រាក់")
    kb.row("━━━ 👥 អ្នកប្រើ ━━━")
    kb.row("👥 អ្នកប្រើប្រាស់",  "📊 ស្ថិតិ")
    kb.row("🎟️ លេខកូដPromo",   "📢 ផ្សព្វផ្សាយ")
    kb.row("⏱ ល្បឿន Poll",     "🔄 ធ្វើឱ្យទាន់សម័យ")
    return kb

def cancel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("✕ Cancel")
    return kb

def lang_select_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇰🇭 ខ្មែរ", callback_data="setlang:kh"),
         InlineKeyboardButton("🇬🇧 English", callback_data="setlang:en")]
    ])

def deposit_amt_kb(uid=None, promo_code=None):
    lang = get_lang(uid) if uid else "kh"
    amts = [1, 2, 5, 10, 20, 50]
    btns = []
    row = []
    for a in amts:
        row.append(InlineKeyboardButton(f"${a}", callback_data=f"dep:{a}"))
        if len(row) == 3:
            btns.append(row); row = []
    if row: btns.append(row)
    btns.append([InlineKeyboardButton(
        "✏️ ផ្ទាល់ខ្លួន" if lang=="kh" else "✏️ Custom",
        callback_data="dep:custom")])
    if promo_code:
        btns.append([InlineKeyboardButton(
            f"🎟️ Promo: {promo_code} ✅", callback_data="dep:clrpromo")])
    else:
        btns.append([InlineKeyboardButton(
            "🎟️ ដាក់ Promo Code" if lang=="kh" else "🎟️ Enter Promo Code",
            callback_data="dep:promo")])
    return InlineKeyboardMarkup(btns)

def game_menu_kb():
    btns = []
    game_ids = ["mobilelegends", "freefire", "roblox", "pubgmobile"]
    game_list = [p for p in products if p["id"] in game_ids]
    for g in game_list:
        btns.append([InlineKeyboardButton(f"{g.get('icon','🎮')} {g['name']}", callback_data=f"game_sel:{g['id']}")])
    btns.append([InlineKeyboardButton("🔙 Back", callback_data="back:main")])
    return InlineKeyboardMarkup(btns)

def smm_cat_kb():
    PLATFORM_ICONS = {
        "tiktok": "🎵", "telegram": "📱", "facebook": "📘",
        "instagram": "📸", "youtube": "▶️", "twitter": "🐦",
        "x": "🐦", "threads": "🧵"
    }
    cats = _smm_get_categories()
    btns = []
    for cat in cats:
        icon = "📱"
        for key, ico in PLATFORM_ICONS.items():
            if key in cat.lower(): icon = ico; break
        btns.append([InlineKeyboardButton(f"{icon}  {cat}", callback_data=f"smmcat:{cat}")])
    btns.append([InlineKeyboardButton("🔙 Back", callback_data="back:main")])
    return InlineKeyboardMarkup(btns)

def smm_svc_kb(cat):
    SVC_ICONS = {
        "follower":"👤","like":"❤️","view":"👁","comment":"💬",
        "share":"🔗","save":"🔖","member":"👥","subscriber":"🔔",
        "watch":"👀","reaction":"😍",
    }
    svcs = _smm_get_svcs_in_cat(cat)
    btns = []
    for slug, s in svcs:
        label = s.get("label", slug)
        icon = "⚡"
        for key, ico in SVC_ICONS.items():
            if key in label.lower(): icon = ico; break
        btns.append([InlineKeyboardButton(f"{icon}  {label}", callback_data=f"smmsvc:{slug}")])
    btns.append([InlineKeyboardButton("🔙 Back", callback_data="back:smmcats")])
    return InlineKeyboardMarkup(btns)

def smm_qty_kb(slug, s):
    sr   = _smm_sell_rate(s["cost_rate"], slug)
    mn   = s.get("min", 100)
    mx   = s.get("max", 100000)
    label= s.get("label", slug)
    first= label.split()[0] if label else slug
    preset = s.get("preset_qtys")
    if preset and isinstance(preset, list):
        qtys = [q for q in preset if mn <= q <= mx]
    else:
        suggestions = [100, 500, 1000, 5000, 10000, 50000]
        qtys = []
        for q in [mn] + suggestions:
            if mn <= q <= mx and q not in qtys: qtys.append(q)
            if len(qtys) >= 6: break
    btns = []
    for q in qtys:
        price = sr * q / 1000
        btns.append([InlineKeyboardButton(
            f"{q:,} {first} — ${price:.2f}", callback_data=f"smmqty:{slug}:{q}")])
    
    btns.append([InlineKeyboardButton("✏️ បញ្ចូលចំនួនផ្ទាល់ខ្លួន (Custom Qty)", callback_data=f"smmcustom:{slug}")])
    
    btns.append([InlineKeyboardButton("🔙 Back", callback_data="back:smmcats")])
    return InlineKeyboardMarkup(btns)

def products_kb():
    btns = [
        [
            InlineKeyboardButton("🎬 Capcut Pro", callback_data="prod:capcut"),
            InlineKeyboardButton("📱 ALIGHT MOTION", callback_data="prod:alightmotion")
        ],
        [
            InlineKeyboardButton("✨ GEMINI PRO", callback_data="prod:gemini"),
            InlineKeyboardButton("🎨 Canva Pro", callback_data="prod:canva")
        ],
        [
            InlineKeyboardButton("🤖 TEST API", callback_data="prod:testapi"),
            InlineKeyboardButton("📄 Adobe Full", callback_data="prod:adobe")
        ],
        [
            InlineKeyboardButton("📦 Email", callback_data="prod:email"),
            InlineKeyboardButton("🟢 Spotify", callback_data="prod:spotify")
        ],
        [
            InlineKeyboardButton("🪟 Microsoft", callback_data="prod:microsoft"),
            InlineKeyboardButton("📄 iLovePdf", callback_data="prod:ilovepdf")
        ],
        [
            InlineKeyboardButton("1 / 3", callback_data="page:1"),
            InlineKeyboardButton("➡️ បន្ទាប់", callback_data="page:next")
        ],
        [
            InlineKeyboardButton("🔄 ផ្ទុកឡើងវិញ", callback_data="reload")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back:main")
        ]
    ]
    return InlineKeyboardMarkup(btns)

def plans_kb(prod_id):
    p = _get_product(prod_id)
    if not p: return InlineKeyboardMarkup([])
    game_ids = ["mobilelegends", "freefire", "roblox", "pubgmobile"]
    btns = []
    for i, plan in enumerate(p.get("plans", [])):
        cnt = _get_plan_stock_count(prod_id, i)
        orig_price = float(plan['price'])
        final_price = _calc_discounted_price(orig_price)
        
        if discount_config.get("active", False):
            price_str = f"<s>${orig_price:.2f}</s> <b>${final_price:.2f}</b> 🔥"
        else:
            price_str = f"<b>${orig_price:.2f}</b>"

        if prod_id in game_ids:
            label = f"✅ {plan['label']} — {price_str}"
            btns.append([InlineKeyboardButton(label, callback_data=f"plan:{prod_id}:{i}")])
        else:
            if cnt == 0:
                label = f"❌ {plan['label']} — {price_str}  [អស់]"
                btns.append([InlineKeyboardButton(label, callback_data=f"plan_oos:{prod_id}:{i}")])
            else:
                label = f"✅ {plan['label']} — {price_str}"
                btns.append([InlineKeyboardButton(label, callback_data=f"plan:{prod_id}:{i}")])
    btns.append([InlineKeyboardButton("🔙 Back", callback_data="back:gamemenu" if prod_id in game_ids else "back:shop")])
    return InlineKeyboardMarkup(btns)

# ═══════════════════════════════════════════════════════════
#  PRODUCT HELPERS
# ═══════════════════════════════════════════════════════════
def _get_product(pid):
    for p in products:
        if p["id"] == pid: return p
    return None

def _stock_key(pid, plan_idx=None):
    if plan_idx is not None:
        return f"{pid}__{plan_idx}"
    return pid

def _get_stock(pid, plan_idx=None):
    key = _stock_key(pid, plan_idx)
    if plan_idx is not None and key in stock:
        return stock.get(key, [])
    if plan_idx is not None:
        return stock.get(pid, [])
    return stock.get(pid, [])

def _get_plan_stock_count(pid, plan_idx):
    key = _stock_key(pid, plan_idx)
    return len(stock.get(key, []))

def _pop_stock(pid, plan_idx=None):
    key = _stock_key(pid, plan_idx)
    s = stock.get(key)
    if s is None and plan_idx is not None:
        s = stock.get(pid, [])
        key = pid
    if not s:
        return None
    item = s.pop(0)
    stock[key] = s
    _save(STOCK_FILE, stock)
    return item

# ═══════════════════════════════════════════════════════════
#  SMM HELPERS
# ═══════════════════════════════════════════════════════════
def _smm_get_categories():
    cats = []
    for s in smm_services.values():
        c = s.get("category", "Other")
        if c not in cats: cats.append(c)
    return cats

def _smm_get_svcs_in_cat(cat):
    return [(slug, s) for slug, s in smm_services.items() if s.get("category") == cat]

def _smm_profit_pct(): return float(smm_profit.get("pct", 20))

def _smm_sell_rate(cost, slug=None):
    s = smm_services.get(slug, {})
    if s.get("custom_price"): 
        base_price = float(s["custom_price"])
    else:
        base_price = round(float(cost) * (1 + _smm_profit_pct() / 100), 4)
    return _calc_discounted_price(base_price)

def _smm_api_post(params, timeout=25):
    url = smm_api.get("url", "")
    if not url: return None
    try:
        r = http.post(url, data=params, timeout=timeout)
        return r.json()
    except Exception as e:
        logger.error(f"{CLR_RED}SMM API: {e}{CLR_RESET}"); return None

def _smm_fetch_service(api_id):
    key = smm_api.get("key", "")
    url = smm_api.get("url", "")
    if not key or not url: return None
    try:
        r = http.post(url, data={"key": key, "action": "services"}, timeout=20)
        for s in r.json():
            if str(s.get("service")) == str(api_id):
                return {
                    "cost_rate": s.get("rate", s.get("min", "0")),
                    "min": int(s.get("min", 100)),
                    "max": int(s.get("max", 100000)),
                    "raw_name": s.get("name", ""),
                }
    except Exception as e: logger.error(f"{CLR_RED}Fetch service: {e}{CLR_RESET}")
    return None

def _smm_clean_name(raw):
    raw = re.sub(r'\s*\[.*?\]\s*', ' ', raw)
    raw = re.sub(r'\s*\(.*?\)\s*', ' ', raw)
    return re.sub(r'\s+', ' ', raw).strip()[:60]

def _smm_service_list_text():
    if not smm_services: return "❌ គ្មាន Service ទេ"
    lines = ["<b>📋 SMM Services</b>\n━━━━━━━━━━━━━━━━━━"]
    for cat in _smm_get_categories():
        lines.append(f"\n📂 <b>{cat}</b>")
        for slug, s in _smm_get_svcs_in_cat(cat):
            sr = _smm_sell_rate(s["cost_rate"], slug)
            lines.append(f"  • {s.get('label',slug)} — ${sr:.2f}/1K")
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════
#  BAKONG KHQR & COUNTDOWN TIMER
# ═══════════════════════════════════════════════════════════
def _generate_khqr(uid, amount, note=""):
    try:
        from bakong_khqr import KHQR
        k = KHQR(BAKONG_TOKEN)
        qr_str = k.create_qr(
            bank_account  = BANK_ACCOUNT,
            merchant_name = MERCHANT_NAME,
            merchant_city = MERCHANT_CITY,
            amount        = round(float(amount), 2),
            currency      = "USD",
            bill_number   = (note or f"uid{uid}")[:25],
            static        = False,
        )
        return qr_str or ""
    except Exception as e:
        logger.error(f"{CLR_RED}[_generate_khqr] ❌ {e}{CLR_RESET}")
    return ""

def _check_bakong(md5, amount, start_ts):
    try:
        from bakong_khqr import KHQR as _BK
        k = _BK(BAKONG_TOKEN)
        status = k.check_payment(str(md5))
        return status == "PAID"
    except Exception as e:
        logger.error(f"{CLR_RED}[_check_bakong] {e}{CLR_RESET}")
    return False

def _watch_deposit(uid, uid_str, dep_id, amount, start_ts, sent_msg_id=None):
    deadline = time.time() + DEPOSIT_EXPIRE_SEC
    last_update_min = -1
    
    while time.time() < deadline:
        dep = store_deps.get(dep_id)
        if not dep or dep.get("status") != "confirmed":
            md5 = dep.get("md5", "") if dep else ""
            if md5 and _check_bakong(md5, amount, start_ts):
                bonus = float(dep.get("bonus", 0))
                total_credit = round(amount + bonus, 2)
                add_bal(uid, total_credit)
                store_deps[dep_id]["status"] = "confirmed"
                _save(STORE_DEP_FILE, store_deps)
                new_b = bal(uid)
                msg = (f"✅ <b>ដាក់លុយបានជោគជ័យ!</b>\n"
                       f"━━━━━━━━━━━━━━━━━━\n"
                       f"💰 បញ្ញើ: <b>${amount:.2f}</b>")
                if bonus > 0:
                    msg += f"\n🎟️ Promo Bonus: <b>+${bonus:.2f}</b>"
                msg += (f"\n💳 Balance: <b>${new_b:.2f}</b>")
                try:
                    bot.send_message(uid, msg, parse_mode="HTML", reply_markup=main_kb(uid))
                except: pass
                try:
                    bot.send_message(ADMIN_ID,
                        f"💰 <b>ដាក់លុយ ✅ (Auto)</b>\n👤 <code>{uid_str}</code>\n"
                        f"💰 ${amount:.2f}" + (f" + Bonus ${bonus:.2f}" if bonus>0 else ""),
                        parse_mode="HTML")
                except: pass
                if sent_msg_id:
                    try:
                        bot.edit_message_caption(
                            chat_id=uid, message_id=sent_msg_id,
                            caption=f"💳 <b>ដាក់ប្រាក់ (បានទូទាត់រួចរាល់ ✅)</b>\n━━━━━━━━━━━━━━━━━━\n💰 ចំនួន: <b>${amount:.2f}</b>",
                            parse_mode="HTML"
                        )
                    except: pass
                return

        rem_sec = int(deadline - time.time())
        current_min = rem_sec // 60
        if current_min != last_update_min and sent_msg_id and rem_sec > 0:
            last_update_min = current_min
            mins_left = rem_sec // 60
            secs_left = rem_sec % 60
            timer_str = f"{mins_left:02d}:{secs_left:02d}"
            try:
                updated_cap = (
                    f"💳 <b>ដាក់ប្រាក់</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"💰 ចំនួន: <b>${amount:.2f}</b>\n"
                    f"⏱ រាប់ថយក្រោយ: <b>{timer_str} នាទី</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📱 <b>Bakong KHQR សម្រាប់ទូទាត់</b>"
                )
                bot.edit_message_caption(chat_id=uid, message_id=sent_msg_id, caption=updated_cap, parse_mode="HTML")
            except: pass

        time.sleep(5)

    dep = store_deps.get(dep_id)
    if dep and dep.get("status") == "pending":
        dep["status"] = "expired"; _save(STORE_DEP_FILE, store_deps)
        try: bot.send_message(uid, "⏰ <b>QR ផុតកំណត់!</b> សូម top up ម្ដងទៀត", parse_mode="HTML")
        except: pass
        if sent_msg_id:
            try:
                bot.edit_message_caption(
                    chat_id=uid, message_id=sent_msg_id,
                    caption=f"💳 <b>ដាក់ប្រាក់ (ផុតកំណត់ ⏰)</b>\n━━━━━━━━━━━━━━━━━━\n💰 ចំនួន: <b>${amount:.2f}</b>",
                    parse_mode="HTML"
                )
            except: pass

def _send_deposit_qr(uid, amount, promo_code=None, label="💳 ដាក់ប្រាក់", bonus=0.0, promo_code_name=None):
    uid_str = str(uid)
    final_amount = amount
    discount = 0
    promo_applied = promo_code_name
    if promo_code and not promo_applied:
        fa, dc, err = apply_promo(uid, code=promo_code, amount=amount)
        if not err:
            final_amount = fa; discount = dc; promo_applied = promo_code

    qr_str = _generate_khqr(uid, final_amount, f"uid={uid} ${final_amount}")
    if not qr_str:
        bot.send_message(uid, "⚠️ មានបញ្ហា Generate QR! ទំនាក់ Admin", parse_mode="HTML")
        return

    try:
        from bakong_khqr import KHQR as _BK
        k = _BK(BAKONG_TOKEN)
        md5_hash = k.generate_md5(qr_str)
    except Exception as e:
        import hashlib
        md5_hash = hashlib.md5(qr_str.encode()).hexdigest()

    dep_id   = f"dep_{uid}_{int(time.time())}"
    start_ts = int(time.time())
    total_credit = round(final_amount + bonus, 2)

    store_deps[dep_id] = {
        "uid": uid_str, "amount": final_amount, "status": "pending",
        "bonus": bonus, "promo": promo_applied or "",
        "md5": md5_hash, "qr_str": qr_str,
    }
    _save(STORE_DEP_FILE, store_deps)

    cap = (f"{label}\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"💰 ចំនួន: <b>${final_amount:.2f}</b>\n"
           f"⏱ រាប់ថយក្រោយ: <b>05:00 នាទី</b>\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"📱 <b>Bakong KHQR សម្រាប់ទូទាត់</b>")
    
    if promo_applied and (bonus > 0 or discount > 0):
        confirm_promo(promo_applied, uid)

    try:
        admin_txt = (
            f"📥 <b>ការស្នើដាក់លុយថ្មី!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 User ID: <code>{uid_str}</code>\n"
            f"💰 ទឹកប្រាក់ស្នើ: <b>${final_amount:.2f}</b>"
        )
        if bonus > 0:
            admin_txt += f"\n🎟️ Bonus Promo: <b>+${bonus:.2f}</b>"
        admin_txt += f"\n💵 សរុបត្រូវបញ្ចូល: <b>${total_credit:.2f}</b>"

        admin_deposit_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ ដាក់ប្រាក់ឱ្យគេ", callback_data=f"manual_dep:approve:{dep_id}"),
                InlineKeyboardButton("❌ កុំដាក់ប្រាក់ឱ្យគេ", callback_data=f"manual_dep:reject:{dep_id}")
            ]
        ])
        bot.send_message(ADMIN_ID, admin_txt, parse_mode="HTML", reply_markup=admin_deposit_kb)
    except Exception as e:
        logger.error(f"{CLR_RED}[deposit] Admin notification error: {e}{CLR_RESET}")

    img_buf = None
    try:
        import base64
        r = http.post(
            "https://api.bakongrelay.com/v1/generate_khqr_image",
            json    = {"qr": qr_str},
            headers = {"Authorization": f"Bearer {BAKONG_TOKEN}", "Content-Type": "application/json"},
            timeout = 10,
        )
        if r.ok and r.json().get("responseCode") == 0:
            img_b64 = r.json().get("data", {}).get("image", "")
            if img_b64:
                if "," in img_b64: img_b64 = img_b64.split(",", 1)[1]
                img_buf = io.BytesIO(base64.b64decode(img_b64))
                img_buf.seek(0); img_buf.name = "khqr.png"
    except Exception:
        pass

    if img_buf is None:
        try:
            import qrcode as _qrc
            qr = _qrc.QRCode(box_size=6, border=2)
            qr.add_data(qr_str); qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            img_buf = io.BytesIO(); img.save(img_buf, format="PNG"); img_buf.seek(0)
        except Exception:
            pass

    sent_msg_id = None
    if img_buf:
        try:
            img_buf.seek(0)
            sent_msg = bot.send_photo(uid, img_buf, caption=cap, parse_mode="HTML")
            sent_msg_id = sent_msg.message_id
        except:
            sent_msg = bot.send_message(uid, f"{cap}\n\n<code>{qr_str}</code>", parse_mode="HTML")
            sent_msg_id = sent_msg.message_id
    else:
        sent_msg = bot.send_message(uid, f"{cap}\n\n<code>{qr_str}</code>", parse_mode="HTML")
        sent_msg_id = sent_msg.message_id

    threading.Thread(target=_watch_deposit,
                     args=(uid, uid_str, dep_id, final_amount, start_ts, sent_msg_id), daemon=True).start()

# ═══════════════════════════════════════════════════════════
#  ORDER HELPERS
# ═══════════════════════════════════════════════════════════
def _make_order_id():
    return f"KZ{int(time.time())%100000:05d}"

def _place_store_order(uid, prod_id, plan_idx):
    p = _get_product(prod_id)
    if not p: return None, "❌ Product រកមិនឃើញ"
    plans = p.get("plans", [])
    if plan_idx >= len(plans): return None, "❌ Plan ខុស"
    plan  = plans[plan_idx]
    price = _calc_discounted_price(float(plan["price"]))
    qty   = int(plan.get("qty", 1))
    
    game_ids = ["mobilelegends", "freefire", "roblox", "pubgmobile"]
    if bal(uid) < price: return None, f"❌ Balance មិនគ្រប់! (Balance: ${bal(uid):.2f})"
    
    if prod_id not in game_ids:
        stock_cnt = _get_plan_stock_count(prod_id, plan_idx)
        if stock_cnt < qty: return None, f"❌ Stock អស់ហើយ! (Available: {stock_cnt})"
        items = [_pop_stock(prod_id, plan_idx) for _ in range(qty)]
    else:
        items = plan.get("items", [])

    ded_bal(uid, price)
    oid = _make_order_id()
    orders[oid] = {
        "uid": str(uid), "prod_id": prod_id, "prod_name": p["name"],
        "plan": plan["label"], "price": price, "qty": qty,
        "items": items, "status": "delivered" if prod_id not in game_ids else "pending_topup", "ts": int(time.time()),
    }
    _save(ORDERS_FILE, orders)
    
    if prod_id not in game_ids:
        remaining = _get_plan_stock_count(prod_id, plan_idx)
        if remaining <= STOCK_ALERT_MIN:
            try:
                alert_txt = (
                    f"⚠️ <b>ជូនដំណឹង Stock!</b>\n"
                    f"📦 {p.get('icon','')} {p['name']} — {plan['label']}\n"
                    f"🔢 នៅសល់: <b>{remaining}</b>"
                )
                if remaining == 0:
                    alert_txt = (
                        f"🚨 <b>Stock អស់ហើយ!</b>\n"
                        f"📦 {p.get('icon','')} {p['name']} — {plan['label']}\n"
                        f"⚠️ ចូល ➕ បន្ថែមស្តុក ភ្លាម!"
                    )
                bot.send_message(ADMIN_ID, alert_txt, parse_mode="HTML")
            except: pass
    return oid, None

def _place_smm_order(uid, slug, qty):
    uid_str = str(uid)
    s = smm_services.get(slug)
    if not s: return None, "❌ Service រកមិនឃើញ"
    sr    = _smm_sell_rate(s["cost_rate"], slug)
    price = sr * qty / 1000
    if bal(uid) < price: return None, f"❌ Balance មិនគ្រប់! (Balance: ${bal(uid):.2f})"
    ded_bal(uid, price)
    key = smm_api.get("key",""); url = smm_api.get("url","")
    res = _smm_api_post({"key": key, "action": "add",
                         "service": s["api_id"], "link": "pending", "quantity": qty})
    api_order_id = str(res.get("order","")) if res else ""
    oid = _make_order_id()
    smm_orders[oid] = {
        "uid": uid_str, "slug": slug, "label": s.get("label",slug),
        "qty": qty, "price": price, "api_order_id": api_order_id,
        "status": "pending", "ts": int(time.time()),
    }
    _save(SMM_ORD_FILE, smm_orders)
    return oid, None

# ═══════════════════════════════════════════════════════════
#  TRACK USER
# ═══════════════════════════════════════════════════════════
def _track_user(message):
    uid = message.chat.id
    uid_str = str(uid)
    u = message.from_user
    users_db[uid_str] = {
        "name":     u.first_name or "",
        "username": u.username or "",
        "last":     int(time.time()),
        "banned":   users_db.get(uid_str, {}).get("banned", False),
    }
    _save(USERS_FILE, users_db)
    wallets.setdefault(uid_str, 0.0)

def is_banned(uid):
    return bool(users_db.get(str(uid), {}).get("banned", False))

# ═══════════════════════════════════════════════════════════
#  START
# ═══════════════════════════════════════════════════════════
@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.chat.id
    waiting.pop(uid, None)
    livechat_users.discard(uid)
    _track_user(message)
    if is_banned(uid):
        bot.send_message(uid, t(uid, "banned")); return
    if uid == ADMIN_ID:
        bot.send_message(uid,
            f"🤖 <b>Panel Admin — Kairozen All-in-One</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <code>{ADMIN_ID}</code>\n"
            f"💹 ចំណេញ SMM: <b>{_smm_profit_pct():.0f}%</b>\n"
            f"🔥 Global Discount: <b>{'ON (' + str(discount_config.get('pct')) + '%)' if discount_config.get('active') else 'OFF'}</b>\n"
            f"⏱ Poll: <b>{smm_poll.get('interval',5)}s</b>\n"
            f"━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML", reply_markup=admin_kb())
        return
    if str(uid) not in user_lang:
        bot.send_message(uid,
            "🌐 <b>ជ្រើសរើសភាសា / Select Language</b>",
            parse_mode="HTML", reply_markup=lang_select_kb())
        return
    _show_welcome(uid)

def _show_welcome(uid):
    b = bal(uid)
    bot.send_message(uid,
        t(uid, "welcome", b),
        parse_mode="HTML",
        reply_markup=main_kb(uid))

# ═══════════════════════════════════════════════════════════
#  CALLBACKS
# ═══════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: c.data.startswith("setlang:"))
def cb_setlang(call):
    uid  = call.message.chat.id
    lang = call.data.split(":")[1]
    user_lang[str(uid)] = lang
    _save(LANG_FILE, user_lang)
    bot.answer_callback_query(call.id, t(uid, "lang_set"))
    try: bot.delete_message(uid, call.message.message_id)
    except: pass
    _show_welcome(uid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("poll:"))
def cb_poll(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: bot.answer_callback_query(call.id); return
    sec = int(call.data.split(":")[1])
    smm_poll["interval"] = sec; _save(SMM_POLL_FILE, smm_poll)
    bot.answer_callback_query(call.id, f"✅ Poll = {sec}s")
    try: bot.edit_message_text(f"✅ Poll Speed = <b>{sec} វិ</b>",
                               chat_id=uid, message_id=call.message.message_id, parse_mode="HTML")
    except: pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("dep:"))
def cb_dep(call):
    uid     = call.message.chat.id
    uid_str = str(uid)
    lang    = get_lang(uid)
    val     = call.data[4:]
    bot.answer_callback_query(call.id)

    if val == "promo":
        waiting[uid] = {"step": "dep_enter_promo", "msg_id": call.message.message_id}
        bot.send_message(uid,
            "🎟️ <b>ដាក់ Promo Code:</b>\n"
            "<i>ឧ: SAVE50 · GIFT1 · FREE</i>" if lang=="kh" else
            "🎟️ <b>Enter Promo Code:</b>\n<i>e.g. SAVE50 · GIFT1</i>",
            parse_mode="HTML", reply_markup=cancel_kb())
        return

    if val == "clrpromo":
        step = waiting.get(uid)
        if isinstance(step, dict): step.pop("promo", None)
        try:
            bot.edit_message_reply_markup(
                chat_id=uid, message_id=call.message.message_id,
                reply_markup=deposit_amt_kb(uid, None))
        except: pass
        return

    if val == "custom":
        waiting[uid] = {"step": "dep_custom", "promo": _get_dep_promo(uid)}
        bot.send_message(uid,
            "✏️ <b>ផ្ញើចំនួន $ ដែលចង់ deposit:</b>" if lang=="kh" else
            "✏️ <b>Send amount $ to deposit:</b>",
            parse_mode="HTML", reply_markup=cancel_kb())
        return

    amount     = float(val)
    promo_code = _get_dep_promo(uid)
    waiting.pop(uid, None)
    _process_deposit(uid, uid_str, amount, promo_code)

def _get_dep_promo(uid):
    step = waiting.get(uid)
    if isinstance(step, dict):
        return step.get("promo")
    return None

def _process_deposit(uid, uid_str, amount, promo_code):
    lang  = get_lang(uid)
    bonus = 0.0
    promo_applied = None

    if promo_code:
        p = promos.get(promo_code.upper())
        if p and (p.get("uses", 0) == 0 or p.get("used", 0) < p.get("uses", 0)):
            if str(uid) not in p.get("user_used", {}):
                if p.get("pct", False):
                    bonus = round(amount * float(p["discount"]) / 100, 2)
                else:
                    bonus = round(float(p["discount"]), 2)
                promo_applied = promo_code.upper()

    _send_deposit_qr(uid, amount,
                     label=f"💳 <b>{'ដាក់ប្រាក់' if lang=='kh' else 'Top Up'}</b>",
                     bonus=bonus, promo_code_name=promo_applied)

@bot.callback_query_handler(func=lambda c: c.data.startswith("manual_dep:"))
def cb_manual_dep(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID:
        bot.answer_callback_query(call.id)
        return

    parts = call.data.split(":")
    action = parts[1]
    dep_id = parts[2]

    dep = store_deps.get(dep_id)
    if not dep:
        bot.answer_callback_query(call.id, "❌ សំណើនេះរកមិនឃើញ ឬផុតកំណត់ហើយ!", show_alert=True)
        return

    target_uid = int(dep["uid"])
    amount = float(dep["amount"])
    bonus = float(dep.get("bonus", 0))
    total_credit = round(amount + bonus, 2)

    if action == "approve":
        if dep.get("status") == "confirmed":
            bot.answer_callback_query(call.id, "⚠️ សំណើនេះបានបញ្ជាក់រួចរាល់ហើយ!", show_alert=True)
            return

        add_bal(target_uid, total_credit)
        dep["status"] = "confirmed"
        _save(STORE_DEP_FILE, store_deps)

        bot.answer_callback_query(call.id, "✅ បានដាក់ប្រាក់ឱ្យគេរួចរាល់!")
        
        try:
            bot.edit_message_text(
                f"✅ <b>បានដាក់ប្រាក់ឱ្យគេរួចរាល់!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 User: <code>{target_uid}</code>\n"
                f"💰 ចំនួន: <b>${total_credit:.2f}</b>",
                chat_id=uid, message_id=call.message.message_id, parse_mode="HTML"
            )
        except Exception:
            pass

        try:
            msg = (f"✅ <b>ដាក់លុយបានជោគជ័យ! (ដោយ Admin)</b>\n"
                   f"━━━━━━━━━━━━━━━━━━\n"
                   f"💰 បញ្ញើ: <b>${amount:.2f}</b>")
            if bonus > 0:
                msg += f"\n🎟️ Bonus: <b>+${bonus:.2f}</b>"
            msg += f"\n💳 សាច់ប្រាក់បច្ចុប្បន្ន: <b>${bal(target_uid):.2f}</b>"
            bot.send_message(target_uid, msg, parse_mode="HTML", reply_markup=main_kb(target_uid))
        except Exception:
            pass

    elif action == "reject":
        dep["status"] = "rejected"
        _save(STORE_DEP_FILE, store_deps)

        bot.answer_callback_query(call.id, "❌ បានបដិសេធសំណើ!")
        
        try:
            bot.edit_message_text(
                f"❌ <b>បានបដិសេធ (កុំដាក់ប្រាក់ឱ្យគេ)!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 User: <code>{target_uid}</code>\n"
                f"💰 ចំនួន: <b>${amount:.2f}</b>",
                chat_id=uid, message_id=call.message.message_id, parse_mode="HTML"
            )
        except Exception:
            pass

        try:
            bot.send_message(target_uid, "❌ សំណើដាក់ប្រាក់របស់អ្នកត្រូវបានបដិសេធដោយ Admin។", parse_mode="HTML")
        except Exception:
            pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("admaddall:"))
def cb_admaddall(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: return
    bot.answer_callback_query(call.id)
    action = call.data.split(":")[1]

    if action == "digital":
        waiting[uid] = "add_product_name"
        bot.send_message(uid, "➕ <b>បញ្ចូលឈ្មោះផលិតផល ឬហ្គេមថ្មី៖</b>", parse_mode="HTML", reply_markup=cancel_kb())
    elif action == "smm":
        cats_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎵 TikTok",    callback_data="smmaddcat:TikTok"),
             InlineKeyboardButton("📘 Facebook",  callback_data="smmaddcat:Facebook")],
            [InlineKeyboardButton("📸 Instagram", callback_data="smmaddcat:Instagram"),
             InlineKeyboardButton("▶️ YouTube",   callback_data="smmaddcat:YouTube")],
            [InlineKeyboardButton("📱 Telegram",  callback_data="smmaddcat:Telegram")],
            [InlineKeyboardButton("✏️ Custom Category", callback_data="smmaddcat:custom")],
        ])
        bot.send_message(uid, "➕ <b>ជ្រើសរើស Category សម្រាប់ SMM Service៖</b>", parse_mode="HTML", reply_markup=cats_kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("game_sel:"))
def cb_game_sel(call):
    uid = call.message.chat.id
    gid = call.data.split(":")[1]
    bot.answer_callback_query(call.id)
    p = _get_product(gid)
    if not p: return
    lang = get_lang(uid)
    plans = p.get("plans", [])
    plan_lines = []
    for i, pl in enumerate(plans):
        orig_price = float(pl['price'])
        final_price = _calc_discounted_price(orig_price)
        if discount_config.get("active", False):
            price_str = f"<s>${orig_price:.2f}</s> <b>${final_price:.2f}</b> 🔥"
        else:
            price_str = f"<b>${orig_price:.2f}</b>"
        plan_lines.append(f"  • {pl['label']} — {price_str}  ✅ Ready")
    plans_txt = "\n".join(plan_lines) if plan_lines else "  (គ្មាន plan)"
    txt = (f"{p.get('icon','🎮')} <b>{p['name']}</b>\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"📋 {p.get('desc','')}\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"📦 Plans:\n{plans_txt}\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"{'ជ្រើស Plan:' if lang=='kh' else 'Choose Plan:'}")
    try:
        bot.edit_message_text(txt, chat_id=uid, message_id=call.message.message_id,
                              parse_mode="HTML", reply_markup=plans_kb(gid))
    except:
        bot.send_message(uid, txt, parse_mode="HTML", reply_markup=plans_kb(gid))

@bot.callback_query_handler(func=lambda c: c.data.startswith("prod:"))
def cb_prod(call):
    uid  = call.message.chat.id
    pid  = call.data[5:]
    bot.answer_callback_query(call.id)
    p = _get_product(pid)
    if not p: return
    lang = get_lang(uid)
    plans = p.get("plans", [])
    plan_lines = []
    for i, pl in enumerate(plans):
        cnt = _get_plan_stock_count(pid, i)
        orig_price = float(pl['price'])
        final_price = _calc_discounted_price(orig_price)
        
        if discount_config.get("active", False):
            price_str = f"<s>${orig_price:.2f}</s> <b>${final_price:.2f}</b> 🔥"
        else:
            price_str = f"<b>${orig_price:.2f}</b>"

        status = "✅ Available" if cnt > 0 else "❌ អស់"
        plan_lines.append(f"  • {pl['label']} — {price_str}  {status}")
    plans_txt = "\n".join(plan_lines) if plan_lines else "  (គ្មាន plan)"
    txt = (f"{p.get('icon','📦')} <b>{p['name']}</b>\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"📋 {p.get('desc','')}\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"📦 Plans:\n{plans_txt}\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"{'ជ្រើស Plan:' if lang=='kh' else 'Choose Plan:'}")
    try: bot.edit_message_text(txt, chat_id=uid, message_id=call.message.message_id,
                                parse_mode="HTML", reply_markup=plans_kb(pid))
    except: bot.send_message(uid, txt, parse_mode="HTML", reply_markup=plans_kb(pid))

@bot.callback_query_handler(func=lambda c: c.data.startswith("plan_oos:"))
def cb_plan_oos(call):
    bot.answer_callback_query(call.id, "❌ Plan នេះស្តុកអស់ហើយ! សូមរង់ចាំ Admin បន្ថែម.", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("plan:"))
def cb_plan(call):
    uid = call.message.chat.id
    bot.answer_callback_query(call.id)
    _, pid, idx = call.data.split(":")
    idx = int(idx)
    p   = _get_product(pid)
    if not p: return
    plan  = p["plans"][idx]
    price = _calc_discounted_price(float(plan["price"]))
    
    game_ids = ["mobilelegends", "freefire", "roblox", "pubgmobile"]
    if pid in game_ids:
        waiting[uid] = {"step": f"order_{pid}_uid", "prod_id": pid, "plan_idx": idx, "price": price}
        if pid == "mobilelegends":
            prompt_text = "⚔️ <b>Mobile Legends</b> — <b>${:.2f}</b>\n━━━━━━━━━━━━━━━━━━\n🎮 សូមបញ្ចូល <b>User ID & Zone ID</b> របស់អ្នក:\n<i>ឧ: 12345678 (1234)</i>".format(price)
        elif pid == "freefire":
            prompt_text = "💎 <b>Free Fire KH/SG</b> — <b>${:.2f}</b>\n━━━━━━━━━━━━━━━━━━\n🎮 សូមបញ្ចូល <b>User ID</b> របស់អ្នក:".format(price)
        elif pid == "roblox":
            prompt_text = "🟥 <b>Roblox</b> — <b>${:.2f}</b>\n━━━━━━━━━━━━━━━━━━\n👤 សូមបញ្ចូល <b>Roblox Username</b> របស់អ្នក:".format(price)
        else:
            prompt_text = "🔫 <b>PUBG Mobile</b> — <b>${:.2f}</b>\n━━━━━━━━━━━━━━━━━━\n🎮 សូមបញ្ចូល <b>Player ID</b> របស់អ្នក:".format(price)
            
        bot.send_message(uid, prompt_text, parse_mode="HTML", reply_markup=cancel_kb())
    else:
        waiting[uid] = {"step": "order_qty", "prod_id": pid, "plan_idx": idx, "price": price}
        bot.send_message(uid,
            f"🛍️ <b>{p['name']}</b> — {plan['label']} — <b>${price:.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔢 សូមបញ្ចូលចំនួន Account (លេខតែមួយ):\nSend a numeric count of accounts:",
            parse_mode="HTML", reply_markup=cancel_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("admprod:"))
def cb_admprod(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: return
    bot.answer_callback_query(call.id)
    parts  = call.data.split(":", 2)
    action = parts[1]
    pid    = parts[2] if len(parts) > 2 else ""
    p      = _get_product(pid)

    game_ids = ["mobilelegends", "freefire", "roblox", "pubgmobile"]
    if action == "stock":
        p_obj = _get_product(pid)
        plans = p_obj.get("plans", []) if p_obj else []
        if pid in game_ids:
            bot.send_message(uid, f"📦 <b>{p_obj['name']}</b> — Game Top Up (No stock file needed, uses ID)", parse_mode="HTML")
            return
        if plans:
            lines = [f"📦 <b>{p_obj['name'] if p_obj else pid}</b> — Stock per Plan\n━━━━━━━━━━━━━━━━━━"]
            for i, pl in enumerate(plans):
                key   = _stock_key(pid, i)
                items = stock.get(key, [])
                lines.append(f"\n<b>{pl['label']}</b> ({len(items)} items)")
                preview = "\n".join(f"• <code>{it['data'] if isinstance(it,dict) else it}</code>" for it in items[:10])
                if preview: lines.append(preview)
                if len(items) > 10: lines.append(f"...+{len(items)-10} more")
            bot.send_message(uid, "\n".join(lines), parse_mode="HTML")
        else:
            items = _get_stock(pid)
            if not items:
                bot.send_message(uid, f"📦 Stock: <b>0</b> items", parse_mode="HTML"); return
            preview = "\n".join(f"• <code>{i}</code>" for i in items[:20])
            more    = f"\n...+{len(items)-20} more" if len(items) > 20 else ""
            bot.send_message(uid,
                f"📦 <b>{p['name'] if p else pid}</b> — Stock: <b>{len(items)}</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n{preview}{more}",
                parse_mode="HTML")

    elif action == "clrstock":
        p_obj  = _get_product(pid)
        plans  = p_obj.get("plans", []) if p_obj else []
        all_keys = [_stock_key(pid, i) for i in range(len(plans))] + [pid]
        total_cnt = sum(len(stock.get(k, [])) for k in all_keys)
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ យល់ព្រម Clear", callback_data=f"admprod:confirmclr:{pid}"),
            InlineKeyboardButton("❌ Cancel",         callback_data=f"admprod:cancel:{pid}"),
        ]])
        bot.send_message(uid,
            f"⚠️ Clear stock <b>{p['name'] if p else pid}</b>?\n"
            f"📦 Items: <b>{total_cnt}</b> នឹងត្រូវលុប!",
            parse_mode="HTML", reply_markup=kb)

    elif action == "confirmclr":
        p_obj = _get_product(pid)
        plans = p_obj.get("plans", []) if p_obj else []
        for i in range(len(plans)):
            stock.pop(_stock_key(pid, i), None)
        stock.pop(pid, None)
        _save(STOCK_FILE, stock)
        bot.send_message(uid
