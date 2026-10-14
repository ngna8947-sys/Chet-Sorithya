# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║     Kairozen All-in-One Bot v4 — カイロゼン                  ║
║     ហាងឌីជីថល · ដាក់លុយ KHQR                                ║
║     Global Discount · Panel Admin                           ║
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
DISCOUNT_FILE   = "aio_discount.json"

PRODUCTS_FILE   = "aio_products.json"
ORDERS_FILE     = "aio_orders.json"
STOCK_FILE      = "aio_stock.json"
STORE_DEP_FILE  = "aio_store_deposits.json"
SEEN_TXN_FILE   = "aio_seen_txn.json"
LIVECHAT_FILE   = "aio_livechat.json"

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
livechat_sessions = _load(LIVECHAT_FILE, {})

waiting         = {}
lang_cooldown   = {}
livechat_users  = set()

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
            "👋 សូស្ដីបង <b>Kairozen カイロゼン</b>!\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🌟 Bot នេះផ្ដល់សេវាកម្ម:\n"
            "🛍️ ទិញផលិតផលឌីជីថល\n"
            "💳 បញ្ចូលលុយ · ជំនួយ\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💰 សាច់ប្រាក់: <b>${:.2f}</b>"
        ),
        "select_lang":   "🌐 ជ្រើសរើសភាសា:",
        "lang_set":      "✅ ភាសាត្រូវបានផ្លាស់ប្ដូរ!",
        "menu":          "🏠 ត្រឡប់ Menu ដើម",
        "banned":        "🚫 គណនីរបស់អ្នកត្រូវបាន ban!",
        "cancel_ok":     "🏠 Menu",
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
            "2️⃣ ចុច <b>🛍️ ហាងឌីជីថល</b> → ជ្រើស ផលិតផល → Plan → ទូទាត់"
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
            "👋 Hello <b>Kairozen カイロゼン</b>!\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🌟 Services available:\n"
            "🛍️ Buy Digital Products\n"
            "💳 Top Up · Support\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💰 Balance: <b>${:.2f}</b>"
        ),
        "select_lang":   "🌐 Select Language:",
        "lang_set":      "✅ Language changed!",
        "menu":          "🏠 Back to Menu",
        "banned":        "🚫 Your account has been banned!",
        "cancel_ok":     "🏠 Menu",
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
            "2️⃣ Tap <b>🛍️ Shop</b> → Choose Product → Plan → Pay"
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
#  KEYBOARDS
# ═══════════════════════════════════════════════════════════
def main_kb(uid=None):
    lang = get_lang(uid) if uid else "kh"
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("🛍️ Shop")
        kb.row("📦 Orders")
        kb.row("💳 Top Up",        "👜 Wallet")
        kb.row("💬 Support",       "💡 How to Use",    "🌐 Language")
    else:
        kb.row("🛍️ ហាងឌីជីថល")
        kb.row("📦 ការបញ្ជាទិញ")
        kb.row("💳 ដាក់ប្រាក់",    "👜 កាបូបលុយ")
        kb.row("💬 ជំនួយ Support", "💡 របៀបប្រើប្រាស់", "🌐 ភាសា / Language")
    return kb

def admin_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🛍️ ផលិតផល",       "📦 ការបញ្ជាទិញ")
    kb.row("📦 ស្តុក",         "➕ បន្ថែមស្តុក",    "➕ បន្ថែមផលិតផល")
    kb.row("➕ បន្ថែមផលិតផលថ្មី", "🔥 បញ្ចុះតម្លៃទាំងអស់")
    kb.row("✏️ កែតម្លៃ",       "💳 ប្រាក់បញ្ញើ")
    kb.row("━━━ 💰 ហិរញ្ញវត្ថុ ━━━")
    kb.row("💰 កាបូបលុយ")
    kb.row("💸 បន្ថែមប្រាក់",   "💔 កាត់ប្រាក់")
    kb.row("━━━ 👥 អ្នកប្រើ ━━━")
    kb.row("👥 អ្នកប្រើប្រាស់",  "📊 ស្ថិតិ")
    kb.row("📢 ផ្សព្វផ្សាយ")
    kb.row("🔄 ធ្វើឱ្យទាន់សម័យ")
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
    return InlineKeyboardMarkup(btns)

def products_list_kb():
    if not products:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ មិនទាន់មានផលិតផលទេ", callback_data="none")],
            [InlineKeyboardButton("🔙 Back", callback_data="back:main")]
        ])
    
    btns = []
    row = []
    for p in products:
        name = p['name']
        pid = p['id']
        row.append(InlineKeyboardButton(f"📦 {name}", callback_data=f"shop_prod:{pid}"))
        if len(row) == 2:
            btns.append(row)
            row = []
    if row:
        btns.append(row)
        
    btns.append([InlineKeyboardButton("🔙 Back", callback_data="back:main")])
    return InlineKeyboardMarkup(btns)

def plans_kb(prod_id):
    p = _get_product(prod_id)
    if not p: return InlineKeyboardMarkup([])
    btns = []
    for i, plan in enumerate(p.get("plans", [])):
        cnt = _get_plan_stock_count(prod_id, i)
        orig_price = float(plan['price'])
        final_price = _calc_discounted_price(orig_price)
        
        if discount_config.get("active", False):
            price_str = f"<s>${orig_price:.2f}</s> <b>${final_price:.2f}</b> 🔥"
        else:
            price_str = f"<b>${orig_price:.2f}</b>"

        if cnt == 0:
            label = f"❌ {plan['label']} — {price_str}  [អស់]"
            btns.append([InlineKeyboardButton(label, callback_data=f"plan_oos:{prod_id}:{i}")])
        else:
            label = f"✅ {plan['label']} — {price_str}"
            btns.append([InlineKeyboardButton(label, callback_data=f"plan:{prod_id}:{i}")])
    btns.append([InlineKeyboardButton("🔙 Back to Shop", callback_data="back:shop")])
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
                    msg += f"\n🎟️ Bonus: <b>+${bonus:.2f}</b>"
                msg += (f"\n💳 Balance: <b>${new_b:.2f}</b>")
                try:
                    bot.send_message(uid, msg, parse_mode="HTML", reply_markup=main_kb(uid))
                except: pass
                try:
                    bot.send_message(ADMIN_ID,
                        f"💰 <b>ដាក់លុយ ✅ (Auto)</b>\n👤 <code>{uid_str}</code>\n"
                        f"💰 ${amount:.2f}",
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
    if dep and dep.get("status"] == "pending":
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

def _send_deposit_qr(uid, amount, label="💳 ដាក់ប្រាក់", bonus=0.0):
    uid_str = str(uid)
    qr_str = _generate_khqr(uid, amount, f"uid={uid} ${amount}")
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
    total_credit = round(amount + bonus, 2)

    store_deps[dep_id] = {
        "uid": uid_str, "amount": amount, "status": "pending",
        "bonus": bonus, "md5": md5_hash, "qr_str": qr_str,
    }
    _save(STORE_DEP_FILE, store_deps)

    cap = (f"{label}\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"💰 ចំនួន: <b>${amount:.2f}</b>\n"
           f"⏱ រាប់ថយក្រោយ: <b>05:00 នាទី</b>\n"
           f"━━━━━━━━━━━━━━━━━━\n"
           f"📱 <b>Bakong KHQR សម្រាប់ទូទាត់</b>")

    try:
        admin_txt = (
            f"📥 <b>ការស្នើដាក់លុយថ្មី!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 User ID: <code>{uid_str}</code>\n"
            f"💰 ទឹកប្រាក់ស្នើ: <b>${amount:.2f}</b>"
        )
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
        if r.ok and r.json().get("responseCode"] == 0:
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
                     args=(uid, uid_str, dep_id, amount, start_ts, sent_msg_id), daemon=True).start()

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
    
    if bal(uid) < price: return None, f"❌ Balance មិនគ្រប់! (Balance: ${bal(uid):.2f})"
    
    stock_cnt = _get_plan_stock_count(prod_id, plan_idx)
    if stock_cnt < qty: return None, f"❌ Stock អស់ហើយ! (Available: {stock_cnt})"
    items = [_pop_stock(prod_id, plan_idx) for _ in range(qty)]

    ded_bal(uid, price)
    oid = _make_order_id()
    orders[oid] = {
        "uid": str(uid), "prod_id": prod_id, "prod_name": p["name"],
        "plan": plan["label"], "price": price, "qty": qty,
        "items": items, "status": "delivered", "ts": int(time.time()),
    }
    _save(ORDERS_FILE, orders)
    
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
            f"🔥 Global Discount: <b>{'ON (' + str(discount_config.get('pct')) + '%)' if discount_config.get('active') else 'OFF'}</b>\n"
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

@bot.callback_query_handler(func=lambda c: c.data.startswith("dep:"))
def cb_dep(call):
    uid     = call.message.chat.id
    uid_str = str(uid)
    lang    = get_lang(uid)
    val     = call.data[4:]
    bot.answer_callback_query(call.id)

    if val == "custom":
        waiting[uid] = {"step": "dep_custom"}
        bot.send_message(uid,
            "✏️ <b>ផ្ញើចំនួន $ ដែលចង់ deposit:</b>" if lang=="kh" else
            "✏️ <b>Send amount $ to deposit:</b>",
            parse_mode="HTML", reply_markup=cancel_kb())
        return

    amount = float(val)
    waiting.pop(uid, None)
    _send_deposit_qr(uid, amount, label=f"💳 <b>{'ដាក់ប្រាក់' if lang=='kh' else 'Top Up'}</b>")

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
        if dep.get("status"] == "confirmed":
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
                   f"💰 បញ្ញើ: <b>${amount:.2f}</b>\n"
                   f"💳 សាច់ប្រាក់បច្ចុប្បន្ន: <b>${bal(target_uid):.2f}</b>")
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
        bot.send_message(uid, "➕ <b>បញ្ចូលឈ្មោះផលិតផលថ្មី៖</b>", parse_mode="HTML", reply_markup=cancel_kb())

# ─── SHOP PHOTO & PRODUCT DISPLAY HANDLERS ───
@bot.callback_query_handler(func=lambda c: c.data.startswith("shop_prod:"))
def cb_shop_prod(call):
    uid  = call.message.chat.id
    pid  = call.data[10:]
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
    
    # Check if product has an image url or file_id stored in 'image' field
    img = p.get("image", None)
    try:
        if img:
            bot.send_photo(uid, img, caption=txt, parse_mode="HTML", reply_markup=plans_kb(pid))
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
        else:
            bot.edit_message_text(txt, chat_id=uid, message_id=call.message.message_id,
                                    parse_mode="HTML", reply_markup=plans_kb(pid))
    except:
        bot.send_message(uid, txt, parse_mode="HTML", reply_markup=plans_kb(pid))

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

    if action == "stock":
        p_obj = _get_product(pid)
        plans = p_obj.get("plans", []) if p_obj else []
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
        txt = f"⚠️ Clear stock <b>{p['name'] if p else pid}</b>?\n📦 Items: <b>{total_cnt}</b> នឹងត្រូវលុប!"
        try:
            bot.edit_message_text(txt, chat_id=uid, message_id=call.message.message_id, parse_mode="HTML", reply_markup=kb)
        except:
            bot.send_message(uid, txt, parse_mode="HTML", reply_markup=kb)

    elif action == "confirmclr":
        p_obj = _get_product(pid)
        plans = p_obj.get("plans", []) if p_obj else []
        for i in range(len(plans)):
            stock.pop(_stock_key(pid, i), None)
        stock.pop(pid, None)
        _save(STOCK_FILE, stock)
        txt = f"✅ Stock <b>{p['name'] if p else pid}</b> cleared (all plans)!"
        try:
            bot.edit_message_text(txt, chat_id=uid, message_id=call.message.message_id, parse_mode="HTML")
        except:
            bot.send_message(uid, txt, parse_mode="HTML")

    elif action == "del":
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ យល់ព្រម Delete", callback_data=f"admprod:confirmdel:{pid}"),
            InlineKeyboardButton("❌ Cancel",          callback_data=f"admprod:cancel:{pid}"),
        ]])
        cnt = len(_get_stock(pid))
        txt = f"⚠️ Delete product <b>{p['name'] if p else pid}</b>?\n📦 Stock: <b>{cnt}</b> items នឹងត្រូវលុបផងដែរ!"
        try:
            bot.edit_message_text(txt, chat_id=uid, message_id=call.message.message_id, parse_mode="HTML", reply_markup=kb)
        except:
            bot.send_message(uid, txt, parse_mode="HTML", reply_markup=kb)

    elif action == "confirmdel":
        name = p["name"] if p else pid
        plans = p.get("plans", []) if p else []
        global products
        products = [x for x in products if x["id"] != pid]
        _save(PRODUCTS_FILE, products)
        for i in range(len(plans)):
            stock.pop(_stock_key(pid, i), None)
        stock.pop(pid, None)
        _save(STOCK_FILE, stock)
        txt = f"✅ Product <b>{name}</b> deleted! (Stock cleared)"
        try:
            bot.edit_message_text(txt, chat_id=uid, message_id=call.message.message_id, parse_mode="HTML")
        except:
            bot.send_message(uid, txt, parse_mode="HTML")

    elif action == "cancel":
        try:
            bot.delete_message(uid, call.message.message_id)
        except:
            pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("addstock_prod:"))
def cb_addstock_prod(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: return
    pid = call.data[len("addstock_prod:"):]
    bot.answer_callback_query(call.id)
    p = _get_product(pid)
    if not p:
        bot.answer_callback_query(call.id, "❌ Product រកមិនឃើញ", show_alert=True); return
    
    plans = p.get("plans", [])
    if not plans:
        bot.answer_callback_query(call.id, "❌ ផលិតផលនេះគ្មាន Plan! សូមបន្ថែម Plan ជាមុន។", show_alert=True); return
    btns = []
    for i, pl in enumerate(plans):
        cnt = _get_plan_stock_count(pid, i)
        status = f"({cnt} នៅ)" if cnt > 0 else "(❌ អស់)"
        btns.append([InlineKeyboardButton(
            f"{pl['label']} — ${pl['price']:.2f}  {status}",
            callback_data=f"addstock_plan:{pid}:{i}")])
    btns.append([InlineKeyboardButton("🔙 Back", callback_data="addstock_back")])
    txt = f"➕ <b>Add Stock — {p.get('icon','')} {p['name']}</b>\n━━━━━━━━━━━━━━━━━━\nជ្រើស Plan ដើម្បីដាក់ stock:"
    try:
        bot.edit_message_text(txt, chat_id=uid, message_id=call.message.message_id, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))
    except:
        bot.send_message(uid, txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))

@bot.callback_query_handler(func=lambda c: c.data.startswith("addstock_plan:"))
def cb_addstock_plan(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: return
    bot.answer_callback_query(call.id)
    _, pid, idx_str = call.data.split(":", 2)
    idx = int(idx_str)
    p   = _get_product(pid)
    if not p: return
    plan = p["plans"][idx]
    waiting[uid] = {"step": "add_stock_items", "pid": pid, "plan_idx": idx}
    cnt = _get_plan_stock_count(pid, idx)
    bot.send_message(uid,
        f"➕ <b>Add Stock</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 {p.get('icon','')} <b>{p['name']}</b>\n"
        f"🏷️ Plan: <b>{plan['label']}</b> — ${plan['price']:.2f}\n"
        f"📊 Stock បច្ចុប្បន្ន: <b>{cnt}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>របៀបដាក់ Stock:</b>\n"
        f"ផ្ញើ accounts <b>1 per line</b>\n\n"
        f"<b>Format:</b>\n"
        f"<code>email:password</code>\n",
        parse_mode="HTML", reply_markup=cancel_kb())

@bot.callback_query_handler(func=lambda c: c.data == "addstock_back")
def cb_addstock_back(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: return
    bot.answer_callback_query(call.id)
    if not products:
        bot.answer_callback_query(call.id, "❌ គ្មាន Product", show_alert=True); return
    btns = []
    for p in products:
        btns.append([InlineKeyboardButton(
            f"{p.get('icon','📦')} {p['name']}", callback_data=f"addstock_prod:{p['id']}")])
    txt = "➕ <b>Add Stock</b>\n━━━━━━━━━━━━━━━━━━\nជ្រើស Product:"
    try:
        bot.edit_message_text(txt, chat_id=uid, message_id=call.message.message_id, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))
    except:
        bot.send_message(uid, txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))

@bot.callback_query_handler(func=lambda c: c.data.startswith("editprice_prod:"))
def cb_editprice_prod(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: return
    pid = call.data[len("editprice_prod:"):]
    bot.answer_callback_query(call.id)
    p = _get_product(pid)
    if not p:
        bot.answer_callback_query(call.id, "❌ Product រកមិនឃើញ", show_alert=True); return
    plans = p.get("plans", [])
    btns  = []
    for i, pl in enumerate(plans):
        btns.append([
            InlineKeyboardButton(
                f"✏️ {pl['label']} — ${pl['price']:.2f}",
                callback_data=f"editprice_plan:{pid}:{i}"),
            InlineKeyboardButton(
                f"✏️ Label", callback_data=f"editlabel_plan:{pid}:{i}"),
            InlineKeyboardButton(
                f"🗑️", callback_data=f"delplan:{pid}:{i}"),
        ])
    btns.append([InlineKeyboardButton(
        "➕ បន្ថែម Plan ថ្មី", callback_data=f"editprice_addplan:{pid}")])
    btns.append([InlineKeyboardButton("🔙 Back", callback_data="editprice_back")])
    txt = (
        f"✏️ <b>Edit Plans — {p.get('icon','')} {p['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"ចុច ✏️ Label ដើម្បីកែឈ្មោះ  |  🗑️ ដើម្បីលុប Plan:"
    )
    try:
        bot.edit_message_text(txt, chat_id=uid, message_id=call.message.message_id,
                              parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))
    except:
        bot.send_message(uid, txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))

@bot.callback_query_handler(func=lambda c: c.data.startswith("editprice_plan:"))
def cb_editprice_plan(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: return
    bot.answer_callback_query(call.id)
    _, pid, idx_str = call.data.split(":", 2)
    idx  = int(idx_str)
    p    = _get_product(pid)
    if not p: return
    plan = p["plans"][idx]
    waiting[uid] = {"step": "edit_price_val", "pid": pid, "plan_idx": idx}
    bot.send_message(uid,
        f"✏️ <b>កែតម្លៃ Plan</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 {p.get('icon','')} <b>{p['name']}</b>\n"
        f"🏷️ Plan: <b>{plan['label']}</b>\n"
        f"💰 តម្លៃបច្ចុប្បន្ន: <b>${plan['price']:.2f}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"ផ្ញើ <b>តម្លៃថ្មី</b> (USD):\n"
        f"<i>ឧ: <code>2.50</code></i>",
        parse_mode="HTML", reply_markup=cancel_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("editprice_addplan:"))
def cb_editprice_addplan(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: return
    pid = call.data[len("editprice_addplan:"):]
    bot.answer_callback_query(call.id)
    p = _get_product(pid)
    if not p: return
    waiting[uid] = {"step": "edit_price_newplan_label", "pid": pid}
    bot.send_message(uid,
        f"➕ <b>បន្ថែម Plan ថ្មី</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 {p.get('icon','')} <b>{p['name']}</b>\n\n"
        f"ផ្ញើ <b>ឈ្មោះ Plan</b>:\n"
        f"<i>ឧ: <code>1 ខែ</code> ឬ <code>100 Diamonds</code></i>",
        parse_mode="HTML", reply_markup=cancel_kb())

@bot.callback_query_handler(func=lambda c: c.data == "editprice_back")
def cb_editprice_back(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: return
    bot.answer_callback_query(call.id)
    if not products:
        bot.answer_callback_query(call.id, "❌ គ្មាន Product", show_alert=True); return
    btns = []
    for p in products:
        btns.append([InlineKeyboardButton(
            f"{p.get('icon','📦')} {p['name']}", callback_data=f"editprice_prod:{p['id']}")])
    txt = "✏️ <b>Edit Price / Plans</b>\n━━━━━━━━━━━━━━━━━━\nជ្រើស Product:"
    try:
        bot.edit_message_text(txt, chat_id=uid, message_id=call.message.message_id,
                              parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))
    except:
        bot.send_message(uid, txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(btns))

@bot.callback_query_handler(func=lambda c: c.data.startswith("editlabel_plan:"))
def cb_editlabel_plan(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: return
    bot.answer_callback_query(call.id)
    _, pid, idx_str = call.data.split(":", 2)
    idx  = int(idx_str)
    p    = _get_product(pid)
    if not p: return
    plan = p["plans"][idx]
    waiting[uid] = {"step": "edit_label_val", "pid": pid, "plan_idx": idx}
    bot.send_message(uid,
        f"✏️ <b>កែឈ្មោះ Plan</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 {p.get('icon','')} <b>{p['name']}</b>\n"
        f"🏷️ ឈ្មោះបច្ចុប្បន្ន: <b>{plan['label']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"ផ្ញើ <b>ឈ្មោះថ្មី</b>:\n<i>ឧ: <code>1 ខែ</code></i>",
        parse_mode="HTML", reply_markup=cancel_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("delplan:"))
def cb_delplan(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: return
    bot.answer_callback_query(call.id)
    _, pid, idx_str = call.data.split(":", 2)
    idx = int(idx_str)
    p   = _get_product(pid)
    if not p: return
    plan = p["plans"][idx]
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ យល់ព្រម លុប", callback_data=f"delplan_ok:{pid}:{idx}"),
        InlineKeyboardButton("❌ Cancel",       callback_data=f"editprice_prod:{pid}"),
    ]])
    txt = f"⚠️ លុប Plan <b>{plan['label']}</b> (${plan['price']:.2f})?"
    try:
        bot.edit_message_text(txt, chat_id=uid, message_id=call.message.message_id, parse_mode="HTML", reply_markup=kb)
    except:
        bot.send_message(uid, txt, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("delplan_ok:"))
def cb_delplan_ok(call):
    uid = call.message.chat.id
    if uid != ADMIN_ID: return
    bot.answer_callback_query(call.id)
    _, pid, idx_str = call.data.split(":", 2)
    idx = int(idx_str)
    p   = _get_product(pid)
    if not p: return
    if idx >= len(p["plans"]): return
    label = p["plans"][idx]["label"]
    p["plans"].pop(idx)
    stock.pop(_stock_key(pid, idx), None)
    _save(PRODUCTS_FILE, products)
    _save(STOCK_FILE, stock)
    try:
        bot.edit_message_text(f"✅ Plan <b>{label}</b> លុបរួចហើយ!", chat_id=uid, message_id=call.message.message_id, parse_mode="HTML")
    except:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("back:"))
def cb_back(call):
    uid = call.message.chat.id
    bot.answer_callback_query(call.id)
    dest = call.data[5:]
    waiting.pop(uid, None)
    livechat_users.discard(uid)
    if dest == "main":
        try:
            bot.delete_message(uid, call.message.message_id)
        except:
            pass
        _show_welcome(uid)
    elif dest == "shop":
        if not products:
            txt = "❌ <b>ហាងកំពុងរៀបចំ</b>\n\nអែតមីនមិនទាន់បានដាក់បញ្ចូលផលិតផល ឬសេវាកម្មណាមួយឡើយ។ សូមអត់ធ្មត់រង់ចាំបន្តិច!"
        else:
            txt = "🛍️ <b>ហាងឌីជីថល</b>\n━━━━━━━━━━━━━━━━━━\n📦 <b>ជ្រើសរើសប្រភេទសេវាកម្ម:</b>"
        try:
            bot.send_photo(uid, products[0].get("image", "https://i.imgur.com/8Q6v3d7.png") if products and products[0].get("image") else "https://i.imgur.com/8Q6v3d7.png", caption=txt, parse_mode="HTML", reply_markup=products_list_kb())
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
        except:
            try:
                bot.edit_message_text(txt, chat_id=uid, message_id=call.message.message_id, parse_mode="HTML", reply_markup=products_list_kb())
            except
