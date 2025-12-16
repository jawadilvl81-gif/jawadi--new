# ===========================
# TELEGRAM BOT - PRIVATE ONLY
# Library: pyTelegramBotAPI
# ===========================

import telebot
from telebot import types
import threading
import time
import random
from datetime import datetime, timedelta
import pytz
from flask import Flask

# ===========================
# HARD-CODED CONFIG
# ===========================
BOT_TOKEN = "7760766537:AAEq7YHiUajTO7Vkpp3Wz-9o0fmEoLUMH_o"
ADMIN_ID = 1319884774

MAIN_CHANNEL = "@minahil_malik_viral_vids"
MAIN_CHANNEL_LINK = "https://t.me/minahil_malik_viral_vids"
BACKUP_CHANNEL = "@paki_leaks_here"
BACKUP_CHANNEL_LINK = "https://t.me/paki_leaks_here"

TZ = pytz.timezone("Asia/Karachi")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ===========================
# FLASK KEEP-ALIVE
# ===========================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive."

def run_flask():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_flask, daemon=True).start()

# ===========================
# GLOBAL STATE
# ===========================
known_users = set()
feedback_mode = set()

temp_broadcast = {
    "active": False,
    "text": None,
    "end_time": None
}

saved_media = None
saved_media_type = None

custom_words = {}      # word -> dict
giveaway = {
    "active": False,
    "participants": set(),
    "end_time": None,
    "winners": 1
}

# ===========================
# UTILITIES
# ===========================
def now_pkt():
    return datetime.now(TZ)

def is_admin(uid):
    return uid == ADMIN_ID

def private_only(message):
    return message.chat.type == "private"

def join_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Join Main Channel", url=MAIN_CHANNEL_LINK))
    kb.add(types.InlineKeyboardButton("Join Backup Channel", url=BACKUP_CHANNEL_LINK))
    return kb

def feedback_button():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💬 Feedback", callback_data="feedback"))
    return kb

def must_join_check(message):
    if is_admin(message.from_user.id):
        return True
    try:
        m1 = bot.get_chat_member(MAIN_CHANNEL, message.from_user.id)
        m2 = bot.get_chat_member(BACKUP_CHANNEL, message.from_user.id)
        if m1.status in ["left", "kicked"] or m2.status in ["left", "kicked"]:
            bot.reply_to(
                message,
                "Bot use karne ke liye pehle dono channels join karo!",
                reply_markup=join_keyboard()
            )
            return False
    except:
        bot.reply_to(
            message,
            "Bot use karne ke liye pehle dono channels join karo!",
            reply_markup=join_keyboard()
        )
        return False
    return True

def log_admin(text):
    try:
        bot.send_message(ADMIN_ID, text)
    except:
        pass

# ===========================
# /START
# ===========================
@bot.message_handler(commands=["start"])
def start_cmd(message):
    if not private_only(message):
        return
    known_users.add(message.from_user.id)

    if not must_join_check(message):
        return

    bot.send_message(
        message.chat.id,
        "Welcome! Bot ready hai. ✅",
        reply_markup=feedback_button()
    )

# ===========================
# /HELP (ADMIN ONLY)
# ===========================
@bot.message_handler(commands=["help"])
def help_cmd(message):
    if not private_only(message):
        return
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "Ye command sirf admin ke liye hai!")
        return

    help_text = (
        "<b>ADMIN COMMANDS</b>\n\n"
        "/allmembers <text> (ya media reply)\n"
        "→ Sab users ko broadcast\n\n"
        "/notify <text> <minutes>\n"
        "→ Temporary broadcast\n\n"
        "/stop\n"
        "→ Temporary broadcast stop\n\n"
        "/channel <text> <delay_minutes>\n"
        "→ Channel scheduled post\n\n"
        "/channel_now <text>\n"
        "→ Channel instant post\n\n"
        "/members <minutes>\n"
        "→ Saved media broadcast\n\n"
        "/giveaway all <minutes> <winners>\n"
        "→ Giveaway start\n\n"
        "/my <word>\n"
        "→ Custom word setup\n\n"
        "/all <my_word>\n"
        "→ Word-based broadcast\n\n"
        "/stats\n"
        "/stats channel\n"
        "/mention <limit> <minutes> <total>\n"
    )
    bot.send_message(message.chat.id, help_text)

# ===========================
# /ALLMEMBERS
# ===========================
@bot.message_handler(commands=["allmembers"])
def allmembers_cmd(message):
    if not private_only(message):
        return
    if not is_admin(message.from_user.id):
        return

    if message.reply_to_message and message.reply_to_message.content_type != "text":
        for uid in list(known_users):
            try:
                bot.copy_message(
                    uid,
                    message.chat.id,
                    message.reply_to_message.message_id,
                    reply_markup=feedback_button()
                )
            except:
                pass
    else:
        text = message.text.replace("/allmembers", "").strip()
        for uid in list(known_users):
            try:
                bot.send_message(uid, text, reply_markup=feedback_button())
            except:
                pass

    bot.reply_to(message, "Message/media sab users ko bhej diya!")

# ===========================
# /NOTIFY & /STOP
# ===========================
@bot.message_handler(commands=["notify"])
def notify_cmd(message):
    if not private_only(message):
        return
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Example: /notify Hello 5")
        return

    minutes = int(parts[-1])
    text = " ".join(parts[1:-1])

    temp_broadcast["active"] = True
    temp_broadcast["text"] = text
    temp_broadcast["end_time"] = now_pkt() + timedelta(minutes=minutes)

    def notifier():
        while temp_broadcast["active"]:
            if now_pkt() >= temp_broadcast["end_time"]:
                temp_broadcast["active"] = False
                break
            time.sleep(5)

    threading.Thread(target=notifier, daemon=True).start()
    bot.reply_to(message, "Temporary broadcast start ho gaya.")

@bot.message_handler(commands=["stop"])
def stop_cmd(message):
    if is_admin(message.from_user.id):
        temp_broadcast["active"] = False
        bot.reply_to(message, "Temporary broadcast stop kar diya.")

# ===========================
# /CHANNEL POSTS
# ===========================
@bot.message_handler(commands=["channel"])
def channel_cmd(message):
    if not private_only(message):
        return
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    delay = int(parts[-1])
    text = " ".join(parts[1:-1])

    def post_later():
        time.sleep(delay * 60)
        bot.send_message(MAIN_CHANNEL, text, disable_web_page_preview=True)

    threading.Thread(target=post_later, daemon=True).start()
    bot.reply_to(message, f"Post schedule ho gaya ({delay} min). PKT time.")

@bot.message_handler(commands=["channel_now"])
def channel_now_cmd(message):
    if is_admin(message.from_user.id):
        text = message.text.replace("/channel_now", "").strip()
        bot.send_message(MAIN_CHANNEL, text, disable_web_page_preview=True)
        bot.reply_to(message, "Channel pe post ho gaya.")

# ===========================
# GIVEAWAY
# ===========================
@bot.message_handler(commands=["giveaway"])
def giveaway_cmd(message):
    if not private_only(message):
        return
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Example: /giveaway all 5 1")
        return

    minutes = int(parts[-2])
    winners = int(parts[-1]) if parts[-1].isdigit() else 1

    giveaway["active"] = True
    giveaway["participants"].clear()
    giveaway["end_time"] = now_pkt() + timedelta(minutes=minutes)
    giveaway["winners"] = winners

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Participate 🎉", callback_data="join_giveaway"))

    announce = (
        "🎁 <b>GIVEAWAY ALERT</b> 🎁\n\n"
        f"⏳ Time: {minutes} minutes\n"
        f"🏆 Winners: {winners}\n\n"
        "Participate karne ke liye button dabao ya 'yes' bhejo!"
    )

    for uid in list(known_users):
        try:
            bot.send_message(uid, announce, reply_markup=kb)
        except:
            pass

    bot.send_message(MAIN_CHANNEL, announce, reply_markup=kb)
    bot.reply_to(message, "Giveaway start ho gaya!")

    def end_giveaway():
        while now_pkt() < giveaway["end_time"]:
            time.sleep(60)
        giveaway["active"] = False

        plist = list(giveaway["participants"])
        if winners > 0 and plist:
            selected = random.sample(plist, min(winners, len(plist)))
        else:
            selected = []

        for uid in selected:
            try:
                bot.send_message(uid, "🏆 Mubarak ho! Aap giveaway jeet gaye! 😍")
            except:
                pass

        log_admin(
            "Giveaway ended!\nWinners:\n" +
            "\n".join([f"{uid}" for uid in selected])
        )

    threading.Thread(target=end_giveaway, daemon=True).start()

@bot.callback_query_handler(func=lambda c: c.data == "join_giveaway")
def join_giveaway_cb(call):
    uid = call.from_user.id
    giveaway["participants"].add(uid)
    bot.answer_callback_query(call.id, "Participated successfully! 😍🥳")
    log_admin(f"User @{call.from_user.username} (ID: {uid}) ne participated kia.")

# ===========================
# FEEDBACK SYSTEM
# ===========================
@bot.callback_query_handler(func=lambda c: c.data == "feedback")
def feedback_cb(call):
    feedback_mode.add(call.from_user.id)
    bot.answer_callback_query(call.id)
    bot.send_message(call.from_user.id, "Apna feedback bhejo! Kaise laga? 😊")

@bot.message_handler(func=lambda m: m.from_user.id in feedback_mode, content_types=["text", "photo", "video", "document"])
def feedback_msg(message):
    feedback_mode.discard(message.from_user.id)
    bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    bot.send_message(
        ADMIN_ID,
        f"Feedback from @{message.from_user.username} (ID: {message.from_user.id})"
    )
    bot.reply_to(message, "Your feedback sent to admin. Thanks! ❤️")

# ===========================
# GENERAL TEXT HANDLER
# ===========================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def text_handler(message):
    if not private_only(message):
        return
    known_users.add(message.from_user.id)
    if not must_join_check(message):
        return

    if temp_broadcast["active"]:
        bot.send_message(
            message.chat.id,
            temp_broadcast["text"],
            reply_markup=feedback_button()
        )

    if giveaway["active"] and message.text.lower() == "yes":
        giveaway["participants"].add(message.from_user.id)
        bot.reply_to(message, "Participated successfully! 😍🥳")
        log_admin(f"User @{message.from_user.username} (ID: {message.from_user.id}) ne participated kia.")

# ===========================
# START BOT
# ===========================
print("Bot running...")
bot.infinity_polling(skip_pending=True)
