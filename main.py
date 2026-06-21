import telebot
import json
import os
import time
import requests
import threading
from datetime import datetime, date, timedelta, timezone
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# TIMEZONE SETUP FOR BANGLADESH TIME
DHAKA_TZ = timezone(timedelta(hours=6))

# ---------- CONFIGURATION ----------
BOT_TOKEN = "8822320722:AAEnQESsJ3klNBlz76MpIFmC8zkPYOOz604"
OWNER_ID = 8179643564
BOT_START_TIME = time.time()

# APIs SETUP (FREE AND 10 VIPS)
FREE_API_URL = "https://bot-bot-bot.vercel.app/like?uid={uid}&server_name=BD"

VIP_APIS = {
    "1": "https://shappno-api.vercel.app/like?uid={uid}&server_name=bd&key=SHAPPNO", 
    "2": "", 
    "3": ""
}

MAX_PUBLIC_LIMIT = 1
MAX_FREE_AUTO_LIKES = 1

# ---------- DATA STORAGE ----------
DB_FILE = "bot_database.json"

class DataManager:
    def __init__(self):
        self.data = {
            "sub_owners": [],           
            "operators": [],
            "allowed_groups": [],
            "public_usage": {},
            "report_group_id": -1003994149489,
            "media": {
                "1": {"name": "START MENU", "type": "none", "url": ""},
                "2": {"name": "LIKE SEND", "type": "none", "url": ""},
                "3": {"name": "VIP LIKE SEND", "type": "none", "url": ""},
                "4": {"name": "AUTO LIKE SEND", "type": "none", "url": ""},
                "5": {"name": "LEADERBOARD", "type": "none", "url": ""},
                "6": {"name": "PROFILE", "type": "none", "url": ""},
                "7": {"name": "OWNER MENU", "type": "none", "url": ""},
                "8": {"name": "ADMIN MENU", "type": "none", "url": ""},
                "9": {"name": "ADMIN/OWNER LIST", "type": "none", "url": ""},
                "10": {"name": "GROUPS LIST", "type": "none", "url": ""},
                "11": {"name": "FREE AUTO LIST", "type": "none", "url": ""},
                "12": {"name": "SCHEDULED AUTO LIST", "type": "none", "url": ""}
            },
            "total_bot_likes": 0,  
            "user_stats": {},       
            "vips": [],                 
            "custom_limits": {},        
            "api_off_until": 0,         
            "api_status": {str(i): True for i in range(1, 11)}, 
            "bot_locked": False,        
            "banned_users": [],         
            "force_join": {"status": False, "channel_id": "@jihadxx24", "link": "https://t.me/jihadxx24"},
            "custom_cmds": {},
            "free_auto_likes": {},  
            "scheduled_auto": {}, # NEW DB ENTRY FOR TIMED AUTO LIKE
            "daily_likes_sts": {},      
            "weekly_likes_sts": {},     
            "monthly_likes_sts": {},    
            "last_daily_reset": str(date.today()),
            "last_weekly_reset": str(date.today().isocalendar()[1]),
            "last_monthly_reset": str(date.today().month),
            "last_auto_run": ""
        }
        self.load()

    def load(self):
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r") as f:
                    loaded_data = json.load(f)
                    for key in self.data:
                        if key in loaded_data:
                            if isinstance(self.data[key], dict) and isinstance(loaded_data[key], dict):
                                self.data[key].update(loaded_data[key])
                            else:
                                self.data[key] = loaded_data[key]
            except Exception as e:
                print(f"DATABASE LOAD ERROR: {e}")
        self.check_reset()

    def save(self):
        with open(DB_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

    def check_reset(self):
        today = date.today()
        if today.strftime("%Y-%m-%d") != self.data.get("last_daily_reset"):
            self.data["public_usage"] = {}
            self.data["daily_likes_sts"] = {}
            self.data["last_daily_reset"] = today.strftime("%Y-%m-%d")
        
        current_week = str(today.isocalendar()[1])
        if current_week != self.data.get("last_weekly_reset"):
            self.data["weekly_likes_sts"] = {}
            self.data["last_weekly_reset"] = current_week
            
        current_month = str(today.month)
        if current_month != self.data.get("last_monthly_reset"):
            self.data["monthly_likes_sts"] = {}
            self.data["last_monthly_reset"] = current_month
            
        self.save()

    def add_sts_record(self, user_id, name, likes):
        user_id_str = str(user_id)
        if user_id_str not in self.data["daily_likes_sts"]: self.data["daily_likes_sts"][user_id_str] = {"name": name, "likes": 0}
        self.data["daily_likes_sts"][user_id_str]["likes"] += likes
        self.data["daily_likes_sts"][user_id_str]["name"] = name
        if user_id_str not in self.data["weekly_likes_sts"]: self.data["weekly_likes_sts"][user_id_str] = {"name": name, "likes": 0}
        self.data["weekly_likes_sts"][user_id_str]["likes"] += likes
        self.data["weekly_likes_sts"][user_id_str]["name"] = name
        if user_id_str not in self.data["monthly_likes_sts"]: self.data["monthly_likes_sts"][user_id_str] = {"name": name, "likes": 0}
        self.data["monthly_likes_sts"][user_id_str]["likes"] += likes
        self.data["monthly_likes_sts"][user_id_str]["name"] = name
        self.save()

db = DataManager()
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ---------- HELPERS ----------
def is_real_owner(user_id):
    return user_id == OWNER_ID

def is_owner(user_id):
    return user_id == OWNER_ID or user_id in db.data.get("sub_owners", [])

def is_admin(user_id):
    return is_owner(user_id) or user_id in db.data["operators"]

def is_vip(user_id, username):
    vips = db.data.get("vips", [])
    if str(user_id) in vips: return True
    if username and str(username).lower().replace("@", "") in vips: return True
    return False

def get_role_details(user_id, username):
    if is_real_owner(user_id): return "REAL OWNER", "👑"
    if is_owner(user_id): return "OWNER", "👑"
    if is_admin(user_id): return "ADMIN", "🛡️"
    if is_vip(user_id, username): return "VIP", "💎"
    return "FREE USER", "⚪"

def get_user_rank(user_id):
    uid_str = str(user_id)
    stats = db.data.get("user_stats", {})
    sorted_users = sorted(stats.items(), key=lambda x: x[1].get('likes_taken', 0), reverse=True)
    for index, (uid, data) in enumerate(sorted_users, 1):
        if uid == uid_str: return index
    return "N/A"

def send_media_msg(chat_id, text, media_key, reply_to, markup=None):
    media_info = db.data.get("media", {}).get(str(media_key), {})
    m_type = media_info.get("type", "none")
    m_url = media_info.get("url", "")
    try:
        if m_type == "video" and m_url:
            return bot.send_video(chat_id, video=m_url, caption=text, parse_mode="HTML", reply_to_message_id=reply_to, reply_markup=markup)
        elif m_type == "photo" and m_url:
            return bot.send_photo(chat_id, photo=m_url, caption=text, parse_mode="HTML", reply_to_message_id=reply_to, reply_markup=markup)
    except Exception: pass
    return bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=True, reply_to_message_id=reply_to, reply_markup=markup)

def is_group_allowed(chat_id):
    if chat_id > 0: return True 
    return chat_id in db.data["allowed_groups"]

def perform_loading(message, title_text="𝐏𝐑𝐎𝐂𝐄𝐒𝐒𝐈𝐍𝐆", sleep_time=0.4):
    wait_msg = bot.reply_to(message, f"⚙️  {title_text}...\n[⬜⬜⬜⬜]     𝐋ᴏᴀᴅɪɴɢ... 0%")
    stages = [
        f"⚙️  {title_text}...\n[🟩⬜⬜⬜]     𝐋ᴏᴀᴅɪɴɢ... 25%",
        f"⚙️  {title_text}...\n[🟩🟩⬜⬜]     𝐋ᴏᴀᴅɪɴɢ... 50%",
        f"⚙️  {title_text}...\n[🟩🟩🟩⬜]     𝐋ᴏᴀᴅɪɴɢ... 75%",
        f"⚙️  {title_text}...\n[🟩🟩🟩🟩]     𝐋ᴏᴀᴅɪɴɢ... 100%"
    ]
    for stage in stages:
        time.sleep(sleep_time)
        try: bot.edit_message_text(stage, message.chat.id, wait_msg.message_id)
        except: pass
    return wait_msg

def is_force_join_required(user_id):
    if is_owner(user_id) or is_admin(user_id): return False
    fj = db.data.get("force_join", {})
    if not fj.get("status", False): return False
    channel_id = fj.get("channel_id", "@jihadxx24")
    try:
        member = bot.get_chat_member(channel_id, user_id)
        if member.status in ['member', 'administrator', 'creator']: return False
    except: pass 
    return True

# ---------- INTERCEPTORS ----------
@bot.message_handler(func=lambda message: message.from_user.id in db.data.get("banned_users", []) and not is_admin(message.from_user.id))
def intercept_banned(message):
    bot.reply_to(message, "🚫 <b>YOU ARE BANNED FROM USING THIS BOT!</b>")

@bot.message_handler(func=lambda message: db.data.get("bot_locked", False) and not is_admin(message.from_user.id), content_types=['text'])
def intercept_locked_bot(message):
    if message.text and message.text.startswith('/'):
        text = (
            "🔒 <b>BOT IS CURRENTLY LOCKED!</b> 🔒\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ THE BOT IS TEMPORARILY DISABLED.\n"
            "ONLY OWNER AND ADMINS CAN USE COMMANDS RIGHT NOW.\n\n"
            "👑 <b>OWNER:</b> @jihadxx240\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        bot.reply_to(message, text)

@bot.message_handler(func=lambda message: message.text and message.text.startswith('/') and is_force_join_required(message.from_user.id))
def force_join_prompt(message):
    fj = db.data.get("force_join", {})
    link = fj.get("link", "https://t.me/jihadxx24")
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📢 JOIN CHANNEL", url=link))
    bot.reply_to(message, "⚠️ <b>ACCESS DENIED!</b>\n\nYOU MUST JOIN OUR OFFICIAL CHANNEL TO USE THIS BOT.", reply_markup=markup, parse_mode="HTML")

def custom_cmd_check(message):
    if not message.text or not message.text.startswith('/'): return False
    cmd_name = message.text.split()[0][1:]
    custom_cmds = db.data.get("custom_cmds", {})
    if cmd_name in custom_cmds: return True
    if cmd_name in custom_cmds.values(): return True 
    return False

@bot.message_handler(func=custom_cmd_check)
def handle_mapped_cmd(message):
    cmd_name = message.text.split()[0][1:]
    custom_cmds = db.data.get("custom_cmds", {})
    
    if cmd_name in custom_cmds.values():
        wait_msg = perform_loading(message, "CHECKING", 0.3)
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ THIS COMMAND HAS BEEN CHANGED BY THE OWNER.")
        
    orig_cmd = custom_cmds[cmd_name]
    if orig_cmd in CMD_FUNCTIONS:
        parts = message.text.split()
        parts[0] = f"/{orig_cmd}"
        message.text = " ".join(parts)
        CMD_FUNCTIONS[orig_cmd](message)

# ---------- START COMMAND & CALLBACKS ----------
@bot.message_handler(commands=['start'])
def cmd_start(message):
    wait_msg = perform_loading(message, "STARTING", 0.3)
    user_name = str(message.from_user.first_name).upper()
    user_id = message.from_user.id
    uname = message.from_user.username
    
    role_name, role_emoji = get_role_details(user_id, uname)

    start_text = (
        "   <b>JIHADX 𝐂𝐎𝐃𝐄𝐗 𝐕𝐈𝐏 𝐁𝐎𝐓  💓💓</b> \n"
        "╔══════════════════╗\n"
        f"👤 <b>𝗨𝗦𝗘𝗥</b>   : {user_name}\n"
        f"🆔 <b>𝗨𝗜𝗗</b>    : <code>{user_id}</code>\n"
        f"{role_emoji} <b>𝗦𝗧𝗔𝗧𝗨𝗦</b> : {role_name}\n"
        "╚══════════════════╝\n\n"
        "⚡ <b>𝗤𝗨𝗜𝗖𝗞 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦</b> ⚡\n"
        "╭━━━━━━━━━━━━━━━━━━╮\n"
        "┃ 💞 <b>/like bd UID</b>\n"
        "┃ ♥️ <b>/auto_like bd UID</b>\n"
        "┃ ✖️ <b>/auto_off UID</b>\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        "📢 <b>𝗖𝗢𝗡𝗡𝗘𝗖𝗧</b> 📢\n"
        "╭━━━━━━━━━━━━━━━━━━╮\n"
        "┃ 👑 <b>OWNER</b>   : @jihadxx240\n"
        "┃ 📣 <b>CHANNEL</b> : @jihadxx24\n"
        "┃ 💬 <b>GROUP</b>   : @tellygram_like_bot\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        "╔══════════════════╗\n"
        "      ✨   JIHADX 𝗖𝗢𝗗𝗘𝗫     ✨\n"
        "╚══════════════════╝"
    )
    
    markup = InlineKeyboardMarkup(row_width=2)
    btn_like = InlineKeyboardButton("😘 LIKE", callback_data="btn_like")
    btn_vip = InlineKeyboardButton("💎 VIP LIKE", callback_data="btn_vip")
    btn_sts = InlineKeyboardButton("📊 STATS", callback_data="btn_sts")
    btn_prof = InlineKeyboardButton("👤 PROFILE", callback_data="btn_prof")
    markup.add(btn_like, btn_vip, btn_sts, btn_prof)

    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass

    send_media_msg(message.chat.id, start_text, "1", message.message_id, markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    bot.answer_callback_query(call.id)
    if call.data == "btn_like":
        bot.send_message(call.message.chat.id, "💡 <b>TO SEND A NORMAL LIKE:</b>\nTYPE: `/like bd UID`", parse_mode="HTML")
    elif call.data == "btn_vip":
        bot.send_message(call.message.chat.id, "💎 <b>TO SEND A VIP LIKE (ADMIN/OWNER):</b>\nTYPE: `/vip_like bd UID`", parse_mode="HTML")
    elif call.data == "btn_sts":
        cmd_sts(call.message)
    elif call.data == "btn_prof":
        show_me(call.message)

# ---------- ADMIN & OWNER MENUS ----------
@bot.message_handler(commands=['owner'])
def cmd_owner_menu(message):
    wait_msg = perform_loading(message, "LOADING OWNER MENU", 0.3)
    if not is_owner(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ <b>ACCESS DENIED:</b> THIS COMMAND IS FOR OWNERS ONLY.")
    text = (
        "🌟 <b>OWNER CONTROL PANEL</b> 🌟\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👑 <b>REAL OWNER EXCLUSIVE:</b>\n"
        "▪️ /owner_add [ID] - ADD SUB-OWNER\n"
        "▪️ /owner_rv [ID] - REMOVE SUB-OWNER\n"
        "▪️ /owner_list - SHOW ALL SUB-OWNERS\n"
        "▪️ /pv  - VIEW MEDIA MAP\n"
        "▪️ /photo [NO.] [LINK] - ADD PHOTO\n"
        "▪️ /video [NO.] [LINK] - ADD VIDEO\n"
        "▪️ /backup & /restore - DATABASE MANAGEMENT\n"
        "▪️ /setting [OLD] [NEW] - CHANGE COMMAND\n\n"
        "🛠️ <b>OWNER CAPABILITIES:</b>\n"
        "▪️ /admin [ID] - ADD ADMIN\n"
        "▪️ /admin_rv [ID] - REMOVE ADMIN\n"
        "▪️ /leave [GROUP ID] - BOT LEAVES GROUP\n"
        "▪️ /on_group [LINK] - ENABLE FORCE JOIN\n"
        "▪️ /off_group - DISABLE FORCE JOIN\n\n"
        "➕ <i>INCLUDES ALL /admin COMMANDS.</i>"
    )
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    send_media_msg(message.chat.id, text, "7", message.message_id)

@bot.message_handler(commands=['admin'])
def cmd_admin_menu(message):
    wait_msg = perform_loading(message, "LOADING ADMIN MENU", 0.3)
    if not is_admin(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ <b>ACCESS DENIED:</b> THIS COMMAND IS FOR ADMINS ONLY.")
        
    args = message.text.split()
    user_id = message.from_user.id
    
    if len(args) == 1:
        text = (
            "🛡️ <b>ADMIN CONTROL PANEL</b> 🛡️\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🛠️ <b>BASIC MANAGEMENT:</b>\n"
            "▪️ /admin list - SHOW ADMIN & OWNER LIST\n"
            "▪️ /groups - SHOW ALLOWED GROUPS\n"
            "▪️ /setgroup [ID] - ALLOW A NEW GROUP\n"
            "▪️ /group_rv [ID] - REMOVE GROUP PERMISSION\n"
            "▪️ /vip_like bd [UID] - SEND VIP LIKE\n\n"
            "⏰ <b>SCHEDULED AUTO LIKE (NEW):</b>\n"
            "▪️ /au_like_ti [REGION] [UID] [TIME] [AM/PM] [DATE]\n"
            "   <i>Ex: /au_like_ti bd 10609031393 04:50 AM 04/05/2026</i>\n"
            "▪️ /au_like_off - CANCEL YOUR SCHEDULED LIKES\n"
            "▪️ /au_like_list - SHOW SCHEDULED LIST\n\n"
            "🔒 <b>BOT LOCK & BAN SYSTEM:</b>\n"
            "▪️ /bot_lock - LOCK THE BOT\n"
            "▪️ /on - UNLOCK THE BOT\n"
            "▪️ /ban [UID] - BAN A USER\n"
            "▪️ /unban [UID] - UNBAN A USER\n\n"
            "💎 <b>VIP & LIMITS SETTINGS:</b>\n"
            "▪️ /add_vip [ID/USERNAME] - ADD VIP\n"
            "▪️ /add_rv_vip [ID/USERNAME] - REMOVE VIP\n"
            "▪️ /set [UID] [LIMIT] - SET USER LIKE LIMIT\n\n"
            "⚙️ <b>API & AUTO LIKE CONTROL:</b>\n"
            "▪️ /api_time - CHECK BOT UPTIME\n"
            "▪️ /free_auto - VIEW FREE AUTO LIST\n"
            "▪️ /off_api [TIME] [S/M/H/D] - TURN OFF ALL APIs\n"
            "▪️ /off_api [1-10] - DISABLE SPECIFIC VIP API\n"
            "▪️ /on_api [1-10] - ENABLE SPECIFIC VIP API\n"
            "▪️ /on_api - TURN ON ALL APIs\n"
            "▪️ /cast [MESSAGE] - BROADCAST MESSAGE\n"
        )
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        send_media_msg(message.chat.id, text, "8", message.message_id)
        
    elif len(args) == 2:
        if args[1].lower() == "list":
            admins = db.data.get("operators", [])
            sub_owners = db.data.get("sub_owners", [])
            list_text = "🛡️ <b>OWNER & ADMIN LIST</b> 🛡️\n━━━━━━━━━━━━━━━━━━━\n"
            list_text += f"👑 <b>REAL OWNER:</b> <code>{OWNER_ID}</code>\n\n"
            
            if sub_owners:
                list_text += "💠 <b>SUB-OWNERS:</b>\n"
                for i, o_id in enumerate(sub_owners, 1):
                    list_text += f"<b>{i}.</b> <code>{o_id}</code>\n"
                list_text += "\n"

            if not admins:
                list_text += "<i>NO ADMINS ADDED YET.</i>\n"
            else:
                list_text += "👮‍♂️ <b>ADMINS:</b>\n"
                for i, admin_id in enumerate(admins, 1):
                    list_text += f"<b>{i}.</b> <code>{admin_id}</code>\n"
            list_text += "━━━━━━━━━━━━━━━━━━━"
            try: bot.delete_message(message.chat.id, wait_msg.message_id)
            except: pass
            return send_media_msg(message.chat.id, list_text, "9", message.message_id)

        if not is_owner(user_id):
            try: bot.delete_message(message.chat.id, wait_msg.message_id)
            except: pass
            return bot.reply_to(message, "❌ ONLY OWNER CAN ADD ADMINS.")
        try:
            new_admin = int(args[1])
            if new_admin not in db.data["operators"]:
                db.data["operators"].append(new_admin)
                db.save()
                res = f"✅ USER <code>{new_admin}</code> HAS BEEN ADDED AS ADMIN."
            else:
                res = "⚠️ THIS USER IS ALREADY AN ADMIN."
            try: bot.delete_message(message.chat.id, wait_msg.message_id)
            except: pass
            bot.reply_to(message, res)
        except: 
            try: bot.delete_message(message.chat.id, wait_msg.message_id)
            except: pass
            bot.reply_to(message, "❌ PROVIDE A VALID ID.")

@bot.message_handler(commands=['owner_add'])
def add_sub_owner(message):
    wait_msg = perform_loading(message, "ADDING OWNER", 0.3)
    if not is_real_owner(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ ONLY THE REAL OWNER CAN USE THIS.")
    try:
        new_owner = int(message.text.split()[1])
        if new_owner not in db.data["sub_owners"]:
            db.data["sub_owners"].append(new_owner)
            db.save()
            res = f"✅ USER <code>{new_owner}</code> ADDED AS SUB-OWNER."
        else: res = "⚠️ USER IS ALREADY A SUB-OWNER."
    except: res = "❌ PROVIDE A VALID ID."
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)

@bot.message_handler(commands=['owner_rv'])
def rv_sub_owner(message):
    wait_msg = perform_loading(message, "REMOVING OWNER", 0.3)
    if not is_real_owner(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ ONLY THE REAL OWNER CAN USE THIS.")
    try:
        old_owner = int(message.text.split()[1])
        if old_owner in db.data["sub_owners"]:
            db.data["sub_owners"].remove(old_owner)
            db.save()
            res = f"🗑️ USER <code>{old_owner}</code> REMOVED FROM SUB-OWNER LIST."
        else: res = "⚠️ USER NOT IN SUB-OWNER LIST."
    except: res = "❌ PROVIDE A VALID ID."
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)

@bot.message_handler(commands=['owner_list'])
def cmd_owner_list(message):
    wait_msg = perform_loading(message, "FETCHING LIST", 0.3)
    if not is_real_owner(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ ONLY REAL OWNER USE THIS....🤫")
    sub_owners = db.data.get("sub_owners", [])
    text = "👑 <b>SUB-OWNER LIST</b> 👑\n━━━━━━━━━━━━━━━━━━━━\n"
    if not sub_owners: text += "<i>NO SUB-OWNERS ADDED.</i>\n"
    for i, o_id in enumerate(sub_owners, 1): text += f"<b>{i}.</b> <code>{o_id}</code>\n"
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    send_media_msg(message.chat.id, text, "9", message.message_id)

# ---------- MEDIA SYSTEM (PHOTO / VIDEO) ----------
@bot.message_handler(commands=['photo_video_list'])
def list_media(message):
    wait_msg = perform_loading(message, "FETCHING MEDIA LIST", 0.3)
    if not is_real_owner(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ ONLY REAL OWNER USE THIS....🤫")
    
    text = "🎨 <b>MEDIA CONFIGURATION LIST</b> 🎨\n━━━━━━━━━━━━━━━━━━━━━\n"
    for k, v in db.data.get("media", {}).items():
        m_type = v.get("type", "none").upper()
        text += f"<b>{k}</b> - {v.get('name', 'UNKNOWN')} - [{m_type}]\n"
        if m_type != "NONE":
            text += f"🔗 <code>{v.get('url', '')}</code>\n"
        text += "━\n"
        
    text += "\n<i>USAGE:</i>\n`/photo [NO.] [LINK]`\n`/video [NO.] [LINK]`"
    
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, text)

@bot.message_handler(commands=['photo', 'video'])
def add_media(message):
    wait_msg = perform_loading(message, f"UPDATING MEDIA", 0.3)
    if not is_real_owner(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ ONLY REAL OWNER USE THIS....🤫")
    cmd = message.text.split()[0].replace("/", "")
    args = message.text.split()
    
    if len(args) < 3:
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, f"⚠️ USAGE: `/{cmd} [LIST NUMBER] [LINK]`")
        
    m_num, m_url = args[1], args[2]
    media_dict = db.data.setdefault("media", {})
    
    if m_num in media_dict:
        media_dict[m_num]["type"] = cmd
        media_dict[m_num]["url"] = m_url
        db.save()
        res = f"✅ <b>SUCCESS!</b>\n{media_dict[m_num]['name']} UPDATED WITH A NEW {cmd.upper()}."
    else:
        res = "❌ INVALID LIST NUMBER. CHECK `/photo_video_list`"

    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)

# ---------- BACKUP & RESTORE ----------
@bot.message_handler(commands=['backup'])
def cmd_backup(message):
    wait_msg = perform_loading(message, "GENERATING BACKUP", 0.3)
    if not is_real_owner(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ ONLY REAL OWNER USE THIS....🤫")
    try:
        with open(DB_FILE, "rb") as f:
            bot.send_document(message.chat.id, f, caption=f"📁 DATABASE BACKUP\nDATE: {datetime.now(DHAKA_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        bot.reply_to(message, f"❌ BACKUP FAILED: {e}")
    finally:
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass

@bot.message_handler(commands=['restore'])
def cmd_restore(message):
    wait_msg = perform_loading(message, "RESTORING DATABASE", 0.5)
    if not is_real_owner(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ ONLY REAL OWNER USE THIS....🤫")
    if not message.reply_to_message or not message.reply_to_message.document:
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "⚠️ YOU MUST REPLY TO A `.json` DATABASE FILE WITH `/restore`")
        
    try:
        file_info = bot.get_file(message.reply_to_message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(DB_FILE, 'wb') as new_file:
            new_file.write(downloaded_file)
        db.load()
        bot.reply_to(message, "✅ <b>DATABASE SUCCESSFULLY RESTORED!</b>")
    except Exception as e:
        bot.reply_to(message, f"❌ RESTORE FAILED: {e}")
    finally:
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass

# ---------- STS (LEADERBOARDS) ----------
@bot.message_handler(commands=['sts'])
def cmd_sts(message):
    wait_msg = perform_loading(message, "FETCHING DAILY STATS", 0.3)
    db.check_reset()
    stats = db.data.get("daily_likes_sts", {})
    sorted_users = sorted(stats.values(), key=lambda x: x.get('likes', 0), reverse=True)
    
    text = "📊 <b>DAILY LEADERBOARD (TOP 10)</b> 📊\n━━━━━━━━━━━━━━━━━━━━\n"
    if not sorted_users: text += "<i>NO DATA AVAILABLE TODAY.</i>\n"
    else:
        for i, u in enumerate(sorted_users[:10], 1): text += f"<b>{i}.</b> {str(u['name']).upper()} = <b>{u['likes']}</b> ❤️\n"
    
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    send_media_msg(message.chat.id, text, "5", message.message_id)

@bot.message_handler(commands=['sts_1'])
def cmd_sts_weekly(message):
    wait_msg = perform_loading(message, "FETCHING WEEKLY STATS", 0.3)
    db.check_reset()
    stats = db.data.get("weekly_likes_sts", {})
    sorted_users = sorted(stats.values(), key=lambda x: x.get('likes', 0), reverse=True)
    
    text = "📊 <b>WEEKLY LEADERBOARD (TOP 10)</b> 📊\n━━━━━━━━━━━━━━━━━━━━\n"
    if not sorted_users: text += "<i>NO DATA AVAILABLE THIS WEEK.</i>\n"
    else:
        for i, u in enumerate(sorted_users[:10], 1): text += f"<b>{i}.</b> {str(u['name']).upper()} = <b>{u['likes']}</b> ❤️\n"
    
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    send_media_msg(message.chat.id, text, "5", message.message_id)

@bot.message_handler(commands=['sts_2'])
def cmd_sts_monthly(message):
    wait_msg = perform_loading(message, "FETCHING MONTHLY STATS", 0.3)
    db.check_reset()
    stats = db.data.get("monthly_likes_sts", {})
    sorted_users = sorted(stats.values(), key=lambda x: x.get('likes', 0), reverse=True)
    
    text = "📊 <b>MONTHLY LEADERBOARD (TOP 10)</b> 📊\n━━━━━━━━━━━━━━━━━━━━\n"
    if not sorted_users: text += "<i>NO DATA AVAILABLE THIS MONTH.</i>\n"
    else:
        for i, u in enumerate(sorted_users[:10], 1): text += f"<b>{i}.</b> {str(u['name']).upper()} = <b>{u['likes']}</b> ❤️\n"
    
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    send_media_msg(message.chat.id, text, "5", message.message_id)

# ---------- SYSTEM COMMANDS ----------
@bot.message_handler(commands=['api_time'])
def cmd_api_time(message):
    wait_msg = perform_loading(message, "CHECKING SYSTEM UPTIME", 0.3)
    if not is_admin(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return
    uptime_sec = int(time.time() - BOT_START_TIME)
    d, rem = divmod(uptime_sec, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    
    text = (
        "⏱️ <b>SYSTEM UPTIME</b> ⏱️\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"API & BOT HAS BEEN RUNNING FOR:\n"
        f"<b>{d} DAYS, {h} HOURS, {m} MINUTES, {s} SECONDS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, text)
@bot.message_handler(commands=['off_api'])
def off_api(message):
    wait_msg = perform_loading(message, "PROCESSING", 0.2)
    if not is_admin(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return
    args = message.text.split()
    
    if len(args) == 2 and args[1].isdigit() and 1 <= int(args[1]) <= 10:
        api_num = args[1]
        db.data["api_status"][api_num] = False
        db.save()
        res = f"✅ VIP API {api_num} SUCCESSFULLY TURNED OFF."
    elif len(args) >= 3:
        try:
            val = float(args[1])
            unit = args[2].lower()
            if unit == 's': mul = 1
            elif unit == 'm': mul = 60
            elif unit == 'h': mul = 3600
            elif unit == 'd': mul = 86400
            else: 
                try: bot.delete_message(message.chat.id, wait_msg.message_id)
                except: pass
                return bot.reply_to(message, "❌ USE S, M, H, OR D.")
            
            db.data["api_off_until"] = float(time.time() + (val * mul))
            db.save()
            res = f"✅ ALL APIs SUCCESSFULLY TURNED OFF FOR {int(val)} {unit.upper()}."
        except: res = "❌ FORMATTING ERROR. FORMAT: `/off_api 2 h`"
    else: res = "⚠️ USAGE: `/off_api [1-10]` OR `/off_api [TIME] [S/M/H/D]`"
    
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)

@bot.message_handler(commands=['on_api'])
def on_api(message):
    wait_msg = perform_loading(message, "PROCESSING", 0.2)
    if not is_admin(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return
    args = message.text.split()
    
    if len(args) == 2 and args[1].isdigit() and 1 <= int(args[1]) <= 10:
        api_num = args[1]
        db.data["api_status"][api_num] = True
        db.save()
        res = f"✅ VIP API {api_num} SUCCESSFULLY TURNED ON."
    else:
        db.data["api_off_until"] = 0
        db.save()
        res = "✅ ALL APIs ARE NOW ON."
        
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)

# ---------- FREE AUTO LIKE ----------
@bot.message_handler(commands=['free_auto'])
def cmd_free_auto(message):
    wait_msg = perform_loading(message, "FETCHING AUTO LIKES", 0.3)
    if not is_admin(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ ADMIN/OWNER ONLY.")
    
    auto_list = db.data.get("free_auto_likes", {})
    text = "🤖 <b>FREE AUTO LIKE LIST (DAILY 4 AM)</b> 🤖\n━━━━━━━━━━━━━━━━━━━━\n"
    if not auto_list:
        text += "<i>NO FREE AUTO LIKES SCHEDULED.</i>"
    else:
        for i, (uid, info) in enumerate(auto_list.items(), 1):
            text += f"<b>{i}.</b> UID: <code>{uid}</code> | ADDED BY: {str(info.get('name', 'N/A')).upper()}\n"
    
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    send_media_msg(message.chat.id, text, "11", message.message_id)

@bot.message_handler(commands=['auto_off'])
def cmd_auto_off(message):
    wait_msg = perform_loading(message, "REMOVING", 0.3)
    args = message.text.split()
    if len(args) < 2: 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "⚠️ FORMAT: `/auto_off UID`")
    uid = args[1]
    
    user_id = message.from_user.id
    auto_list = db.data.setdefault("free_auto_likes", {})
    
    if uid in auto_list:
        if is_admin(user_id) or auto_list[uid]["user_id"] == user_id:
            del auto_list[uid]
            db.save()
            res = f"✅ UID <code>{uid}</code> HAS BEEN REMOVED FROM FREE AUTO LIKE SCHEDULE."
        else:
            res = "❌ YOU DON'T HAVE PERMISSION TO REMOVE THIS UID."
    else:
        res = "⚠️ UID NOT FOUND IN FREE AUTO LIKE SCHEDULE."
        
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)

@bot.message_handler(commands=['auto_like'])
def cmd_auto_like(message):
    wait_msg = perform_loading(message, "ADDING TO SCHEDULE", 0.3)
    args = message.text.split()
    user_id = message.from_user.id
    uname = message.from_user.username
    
    if len(args) < 3:
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "⚠️ FORMAT: `/auto_like bd UID`")
        
    if not is_vip(user_id, uname) and not is_admin(user_id):
        user_auto_likes = [v for k, v in db.data.get("free_auto_likes", {}).items() if v.get("user_id") == user_id]
        if len(user_auto_likes) >= MAX_FREE_AUTO_LIKES:
            try: bot.delete_message(message.chat.id, wait_msg.message_id)
            except: pass
            return bot.reply_to(message, f"❌ FREE USERS CAN ONLY ADD UP TO {MAX_FREE_AUTO_LIKES} AUTO LIKES.")
            
    region, uid = args[1].lower(), args[2]
    
    db.data.setdefault("free_auto_likes", {})[uid] = {
        "region": region, 
        "uid": uid, 
        "user_id": user_id, 
        "chat_id": message.chat.id,
        "name": message.from_user.first_name
    }
    db.save()
    
    res = f"✅ <b>SUCCESSFULLY SCHEDULED!</b>\nUID: <code>{uid}</code> ADDED TO FREE AUTO LIKE.\nLIKES WILL BE SENT DAILY AT 4:00 AM (BD TIME).\n<i>TO CANCEL: `/auto_off {uid}`</i>"
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)

# ---------- NEW SCHEDULED AUTO LIKE SYSTEM ----------
@bot.message_handler(commands=['au_like_ti'])
def cmd_au_like_ti(message):
    wait_msg = perform_loading(message, "SCHEDULING TIME", 0.4)
    if not is_admin(message.from_user.id):
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ <b>ACCESS DENIED:</b> ONLY ADMINS AND OWNERS CAN SCHEDULE SPECIFIC TIME AUTO LIKES.")
        
    args = message.text.split()
    if len(args) < 6:
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "⚠️ <b>WRONG FORMAT!</b>\nUSE: `/au_like_ti [REGION] [UID] [TIME] [AM/PM] [DATE]`\nEXAMPLE: `/au_like_ti bd 10609031393 04:50 AM 04/05/2026`")
        
    try:
        region = args[1].upper()
        uid = args[2]
        time_str = f"{args[3]} {args[4].upper()} {args[5]}"
        dt = datetime.strptime(time_str, "%I:%M %p %d/%m/%Y")
        dt = dt.replace(tzinfo=DHAKA_TZ)
        trigger_ts = dt.timestamp()
        
        user_id = message.from_user.id
        uname = str(message.from_user.first_name).upper()
        
        sched_id = f"{uid}_{trigger_ts}"
        db.data.setdefault("scheduled_auto", {})[sched_id] = {
            "uid": uid,
            "region": region,
            "trigger_ts": trigger_ts,
            "user_id": user_id,
            "name": uname,
            "chat_id": message.chat.id,
            "time_str": time_str
        }
        db.save()
        res = f"✅ <b>AUTO LIKE SCHEDULED SUCCESSFULLY!</b>\nUID: <code>{uid}</code>\nREGION: {region}\nEXACT TIME: {time_str}"
    except Exception as e:
        res = "❌ <b>INVALID DATE/TIME FORMAT.</b> PLEASE USE `HH:MM AM/PM DD/MM/YYYY` EXACTLY.\nEXAMPLE: `04:50 AM 04/05/2026`"

    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)
@bot.message_handler(commands=['au_like_off'])
def cmd_au_like_off(message):
    wait_msg = perform_loading(message, "CANCELLING SCHEDULER", 0.4)
    if not is_admin(message.from_user.id):
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ <b>ACCESS DENIED.</b>")
        
    user_id = message.from_user.id
    scheduled = db.data.setdefault("scheduled_auto", {})
    to_delete = [k for k, v in scheduled.items() if v["user_id"] == user_id]
    
    for k in to_delete:
        del scheduled[k]
        
    if to_delete:
        db.save()
        res = f"✅ <b>SUCCESS:</b> ALL YOUR SCHEDULED UIDS ({len(to_delete)}) HAVE BEEN DELETED FROM THE AUTO_TIME LIST."
    else:
        res = "⚠️ YOU HAVE NO SCHEDULED AUTO LIKES TO CANCEL."
        
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)

@bot.message_handler(commands=['au_like_list'])
def cmd_au_like_list(message):
    wait_msg = perform_loading(message, "FETCHING SCHEDULES", 0.3)
    if not is_admin(message.from_user.id):
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ <b>ACCESS DENIED.</b>")
        
    scheduled = db.data.get("scheduled_auto", {})
    text = "⏰ <b>SCHEDULED AUTO LIKE LIST</b> ⏰\n━━━━━━━━━━━━━━━━━━━━\n"
    if not scheduled:
        text += "<i>NO TIMED AUTO LIKES SCHEDULED.</i>"
    else:
        i = 1
        for k, v in scheduled.items():
            text += f"<b>{i}.</b> UID: <code>{v['uid']}</code> | BY: {v['name']}\n⏱️ TIME: {v['time_str']}\n"
            i += 1
            
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    send_media_msg(message.chat.id, text, "12", message.message_id)

# ---------- LIKE CORE SYSTEM (PUBLIC / FREE) ----------
@bot.message_handler(commands=['like'])
def handle_like(message):
    wait_msg = perform_loading(message, "CHECKING ACCESS", 0.2)
    if not is_group_allowed(message.chat.id):
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message,
            "╔════════════════╗\n"
            "              ❌ NOTICE ❌\n"
            "╚════════════════╝\n\n"
            "🚫 THIS GROUP IS NOT APPROVED\n\n"
            "👤 CONTACT TO OWNER\n"
            "🔗 @jihadxx240\n\n"
            "🔥 JOIN FREE LIKE GROUP\n"
            "🔗 @tellygram_like_bot\n\n"
            "⚠️ FOLLOW THE RULES"
        )
    user_id = message.from_user.id
    uname = message.from_user.username
    args = message.text.split()
    
    off_until = db.data.get("api_off_until", 0)
    now_time = time.time()
    
    if now_time < off_until and not is_admin(user_id):
        rem = int(off_until - now_time)
        m, s = divmod(rem, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        time_str = f"{d} DAY(S) {h} HOUR(S) {m} MINUTE(S) {s} SECOND(S)"
        on_time = datetime.fromtimestamp(off_until, DHAKA_TZ).strftime('%d-%b-%Y, %I:%M %p')
        msg = f"⚠️ <b>𝗔𝗣𝗜 𝗧𝗘𝗠𝗣𝗢𝗥𝗔𝗥𝗜𝗟𝗬 𝗢𝗙𝗙𝗟𝗜𝗡𝗘</b> ⚠️\n━━━━━━━━━━━━━━━━━━━━━\n⏳ <b>𝗔𝗣𝗜 𝗪𝗜𝗟𝗟 𝗕𝗘 𝗢𝗡:</b> {on_time}\n⏱️ <b>𝗥𝗘𝗠𝗔𝗜𝗡𝗜𝗡𝗚 𝗧𝗜𝗠𝗘:</b> {time_str}\n━━━━━━━━━━━━━━━━━━━━━"
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, msg)

    if len(args) < 3: 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "⚠️ FORMAT: `/like bd UID`")

    region, uid = args[1].lower(), args[2]
    db.check_reset()
    usage = db.data["public_usage"].get(str(user_id), 0)
    custom_limit = db.data.get("custom_limits", {}).get(str(user_id), MAX_PUBLIC_LIMIT)
    
    if usage >= custom_limit and not is_admin(user_id):
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, f"💔 DAILY LIMIT REACHED ({usage}/{custom_limit}).")

    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    wait_msg = perform_loading(message, "SENDING LIKES", 1.0)
    
    try:
        req = requests.get(FREE_API_URL.format(region=region.upper(), uid=uid), timeout=27)
        res = req.json()
        
        if "LikesafterCommand" in res:
            if not is_admin(user_id): db.data["public_usage"][str(user_id)] = usage + 1
            
            player_name = str(res.get('PlayerNickname', 'N/A')).upper()
            after_like = res.get('LikesafterCommand', 0)
            before_like = res.get('LikesbeforeCommand')
            
            if before_like is not None: added_likes = after_like - before_like
            else: added_likes = 1; before_like = after_like - added_likes

            is_vip_user = is_admin(user_id) or is_vip(user_id, uname)
            if not is_vip_user and added_likes > 25: added_likes = 25; after_like = before_like + added_likes

            db.data["total_bot_likes"] = db.data.get("total_bot_likes", 0) + added_likes
            display_name = f"@{uname}".upper() if uname else str(message.from_user.first_name).upper()
            db.add_sts_record(user_id, display_name, added_likes)
            
            user_id_str = str(user_id)
            if user_id_str not in db.data["user_stats"]: db.data["user_stats"][user_id_str] = {"name": display_name, "likes_taken": 0}
            db.data["user_stats"][user_id_str]["name"] = display_name
            db.data["user_stats"][user_id_str]["likes_taken"] += added_likes
            db.save()
            
            success_msg = (
                "   <b>𝐋𝐈𝐊𝐄 𝐒𝐄𝐍𝐓 𝐒𝐔𝐂𝐂𝐄𝐒𝐒</b> \n"
                "╔═════════════════╗\n"
                f"👤 <b>𝗣𝗟𝗔𝗬𝗘𝗥</b>  : {player_name}\n"
                f"🆔 <b>𝗨𝗜𝗗</b>     : <code>{uid}</code>\n"
                f"🌐 <b>𝗥𝗘𝗚𝗜𝗢𝗡</b>  : {region.upper()}\n"
                "╚═════════════════╝\n"
                "╭━━━━━━━━━━━━━━━━╮\n"
                f"💝 <b>𝗕𝗘𝗙𝗢𝗥𝗘</b> : {before_like}\n"
                f"💞 <b>𝗔𝗙𝗧𝗘𝗥</b>    : {after_like}\n"
                f"➕ <b>𝗔𝗗𝗗𝗘𝗗</b>  : {added_likes}\n"
                "╰━━━━━━━━━━━━━━━━╯\n\n"
                "╔═════════════════╗\n"
                "👑   JIHADX 𝗖𝗢𝗗𝗘𝗫 👑\n"
                "╚═════════════════╝"
            )
            
            try: bot.delete_message(message.chat.id, wait_msg.message_id)
            except: pass
            
            send_media_msg(message.chat.id, success_msg, "2", message.message_id)

        else: bot.edit_message_text(f"❌ API ERROR OR PLAYER NOT FOUND.", message.chat.id, wait_msg.message_id)
    except Exception as e: 
        bot.edit_message_text(f"❌ SERVER TIMEOUT / FAILED TO FETCH DATA. TRY AGAIN.", message.chat.id, wait_msg.message_id)

# ---------- VIP LIKE SYSTEM (OWNER/ADMIN ONLY, 10 APIs) ----------
@bot.message_handler(commands=['vip_like'])
def handle_vip_like(message):
    wait_msg = perform_loading(message, "VERIFYING ACCESS", 0.3)
    user_id = message.from_user.id
    if not is_admin(user_id):
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ ONLY OWNERS AND ADMINS CAN USE THIS COMMAND.")

    args = message.text.split()
    if len(args) < 3: 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "⚠️ FORMAT: `/vip_like bd UID`")

    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    wait_msg = perform_loading(message, "SENDING VIP LIKES", 1.0)
    region, uid = args[1].lower(), args[2]
    
    player_name = "N/A"
    final_after = 0
    final_before = 0
    total_added = 0
    api_status_rows = ""
    success_count = 0
    
    for i in range(1, 11):
        api_key = str(i)
        if not db.data.get("api_status", {}).get(api_key, True): continue
        
        url = VIP_APIS.get(api_key)
        if not url: continue
        
        try:
            req = requests.get(url.format(uid=uid, region=region.upper()), timeout=26)
            res = req.json()
            if "LikesafterCommand" in res:
                success_count += 1
                player_name = str(res.get('PlayerNickname', player_name)).upper()
                after = res.get('LikesafterCommand', 0)
                before = res.get('LikesbeforeCommand')
                
                if before is not None:
                    added = after - before
                    if final_before == 0 or before < final_before:
                        final_before = before
                else:
                    added = 1
                    if final_before == 0:
                        final_before = after - added
                
                final_after = max(final_after, after)
                total_added += added
                api_status_rows += f"✨ <b>API {api_key} :</b> {added}\n"
        except Exception: 
            pass
            
    if success_count == 0:
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ ALL VIP APIs FAILED OR TIMED OUT. PLEASE TRY AGAIN.")
        
    db.check_reset()
    uname = message.from_user.username
    display_name = f"@{uname}".upper() if uname else str(message.from_user.first_name).upper()
    
    if total_added > 0:
        db.data["total_bot_likes"] = db.data.get("total_bot_likes", 0) + total_added
        db.add_sts_record(user_id, display_name, total_added)
        db.save()
        
    success_msg = (
        "   <b>𝐋𝐈𝐊𝐄 𝐒𝐄𝐍𝐓 𝐒𝐔𝐂𝐂𝐄𝐒𝐒 (VIP)</b> \n"
        "╔═════════════════╗\n"
        f"👤 <b>𝗣𝗟𝗔𝗬𝗘𝗥</b>  : {player_name}\n"
        f"🆔 <b>𝗨𝗜𝗗</b>     : <code>{uid}</code>\n"
        f"🌐 <b>𝗥𝗘𝗚𝗜𝗢𝗡</b>  : {region.upper()}\n"
        "╚═════════════════╝\n"
        "╭━━━━━━━━━━━━━━━━╮\n"
        f"💝 <b>𝗕𝗘𝗙𝗢𝗥𝗘</b> : <b>{final_before}</b>\n"
        f"💞 <b>𝗔𝗙𝗧𝗘𝗥</b>    : {final_after}\n"
        f"{api_status_rows}"
        f"➕ <b>TOTAL</b>  : <b>{total_added}</b>\n"
        "╰━━━━━━━━━━━━━━━━╯\n\n"
        "⚡ <b>𝗦𝗧𝗔𝗧𝗨𝗦</b> : <b>𝗔𝗟𝗪𝗔𝗬𝗦 𝗥𝗘𝗔𝗗𝗬 𝗧𝗢 𝗗𝗘𝗟𝗜𝗩𝗘𝗥 𝗚𝗜𝗩𝗘𝗡 𝗟𝗜𝗞𝗘𝗦 💞</b>\n\n"
        "╔═════════════════╗\n"
        "  👑     JIHADX 𝗖𝗢𝗗𝗘𝗫  👑\n"
        "╚═════════════════╝"
    )

    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass

    send_media_msg(message.chat.id, success_msg, "3", message.message_id)

# ---------- REMAINING SYSTEM COMMANDS ----------
@bot.message_handler(commands=['me'])
def show_me(message):
    wait_msg = perform_loading(message, "FETCHING STATS", 0.3)
    uid_str = str(message.from_user.id)
    uname = message.from_user.username
    stats = db.data.get("user_stats", {}).get(uid_str, {"likes_taken": 0})
    likes_taken = stats.get("likes_taken", 0)
    usage = db.data.get("public_usage", {}).get(uid_str, 0)
    custom_limit = db.data.get("custom_limits", {}).get(uid_str, MAX_PUBLIC_LIMIT)
    
    role_name, role_emoji = get_role_details(message.from_user.id, uname)
    rank = get_user_rank(message.from_user.id)

    text = (
        "╭━━━〔 👤 PROFILE 〕━━━╮\n"
        f"👤 <b>NAME</b>  : {str(message.from_user.first_name).upper()}\n"
        f"🆔 <b>ID</b>    : <code>{message.from_user.id}</code>\n"
        f"{role_emoji} <b>ROLE</b>  : {role_name}\n"
        "━━━━━━━━━━━━━━\n"
        f"❤️ <b>TOTAL LIKES</b> : {likes_taken}\n"
        f"📊 <b>RANK</b>        : #{rank}\n"
        f"⚡ <b>TODAY USED</b>  : {usage}/{custom_limit}\n"
        "╰━━━━━━━━━━━━━━╯"
    )
    
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    
    send_media_msg(message.chat.id, text, "6", message.message_id)

@bot.message_handler(commands=['setting'])
def cmd_setting(message):
    wait_msg = perform_loading(message, "UPDATING SETTING", 0.3)
    if not is_real_owner(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ ONLY REAL OWNER USE THIS....🤫")
    args = message.text.split()
    if len(args) < 3:
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "⚠️ USAGE: `/setting [OLD_COMMAND] [NEW_COMMAND]`\nEXAMPLE: `/setting start begin`")
    
    old_cmd, new_cmd = args[1].replace("/", ""), args[2].replace("/", "")
    if old_cmd not in CMD_FUNCTIONS:
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, f"❌ ORIGINAL COMMAND '{old_cmd}' NOT FOUND.")
    
    db.data["custom_cmds"] = {k: v for k, v in db.data.get("custom_cmds", {}).items() if v != old_cmd}
    db.data["custom_cmds"][new_cmd] = old_cmd
    db.save()
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, f"✅ COMMAND CHANGED SUCCESSFULLY!\nFROM NOW ON, USE `/{new_cmd}` INSTEAD OF `/{old_cmd}`.")

@bot.message_handler(commands=['cast'])
def cmd_cast(message):
    wait_msg = perform_loading(message, "STARTING BROADCAST", 0.3)
    if not is_admin(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ ADMIN/OWNER ONLY.")
    text = message.text.replace("/cast", "").strip().upper()
    if not text: 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "⚠️ USAGE: `/cast [MESSAGE]`")
        
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, "😘 BROADCAST STARTED...")
    
    def broadcast():
        users = list(db.data.get("user_stats", {}).keys())
        groups = db.data.get("allowed_groups", [])
        sent = 0
        for u in users:
            try: 
                bot.send_message(int(u), f"📢 <b>BROADCAST MESSAGE</b>\n━━━━━━━━━━━━━━━━━━━━\n{text}", parse_mode="HTML")
                sent += 1
                time.sleep(0.05)
            except: pass
        for g in groups:
            try:
                bot.send_message(g, f"📢 <b>BROADCAST MESSAGE</b>\n━━━━━━━━━━━━━━━━━━━━\n{text}", parse_mode="HTML")
                sent += 1
                time.sleep(0.05)
            except: pass
        try: bot.send_message(message.chat.id, f"✅ BROADCAST FINISHED! SENT TO {sent} CHATS.")
        except: pass
    threading.Thread(target=broadcast, daemon=True).start()

@bot.message_handler(commands=['admin_rv'])
def rv_admin(message):
    wait_msg = perform_loading(message, "REMOVING", 0.3)
    if not is_owner(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ ONLY OWNER CAN REMOVE ADMINS.")
    args = message.text.split()
    if len(args) < 2: 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "⚠️ USAGE: /admin_rv [ID]")
    try:
        admin_id = int(args[1])
        if admin_id in db.data["operators"]:
            db.data["operators"].remove(admin_id)
            db.save()
            res = f"🗑️ USER <code>{admin_id}</code> REMOVED FROM ADMIN LIST."
        else: res = "⚠️ THIS USER IS NOT IN THE ADMIN LIST."
    except: res = "❌ PROVIDE A VALID ID."
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)

@bot.message_handler(commands=['setgroup'])
def set_group(message):
    wait_msg = perform_loading(message, "PROCESSING", 0.3)
    if not is_admin(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return
    try:
        g_id = int(message.text.split()[1])
        if g_id not in db.data["allowed_groups"]:
            db.data["allowed_groups"].append(g_id)
            db.save()
            res = f"✅ GROUP <code>{g_id}</code> ADDED."
        else: res = "⚠️ GROUP ALREADY ADDED."
    except: res = "USAGE: /setgroup -100xxxxxxxx"
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)

@bot.message_handler(commands=['group_rv'])
def rv_group(message):
    wait_msg = perform_loading(message, "PROCESSING", 0.3)
    if not is_admin(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return
    try:
        g_id = int(message.text.split()[1])
        if g_id in db.data["allowed_groups"]:
            db.data["allowed_groups"].remove(g_id)
            db.save()
            res = f"🗑️ GROUP <code>{g_id}</code> REMOVED."
        else: res = "⚠️ GROUP NOT FOUND."
    except: res = "USAGE: /group_rv -100xxxxxxxx"
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)

@bot.message_handler(commands=['groups'])
def list_groups(message):
    wait_msg = perform_loading(message, "FETCHING GROUPS", 0.3)
    if not is_admin(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    if not db.data["allowed_groups"]: return bot.reply_to(message, "📁 NO GROUPS.")
    res = "📋 <b>ALLOWED GROUPS:</b>\n\n" + "\n".join([f"• <code>{i}</code>" for i in db.data["allowed_groups"]])
    send_media_msg(message.chat.id, res, "10", message.message_id)

@bot.message_handler(commands=['add_vip'])
def cmd_add_vip(message):
    wait_msg = perform_loading(message, "PROCESSING", 0.3)
    if not is_admin(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return
    args = message.text.split()
    if len(args) < 2: 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "USAGE: /add_vip ID_OR_USERNAME")
    target = args[1].lower().replace("@", "")
    if target not in db.data.setdefault("vips", []):
        db.data["vips"].append(target)
        db.save()
    res = f"✅ <code>{target}</code> IS NOW VIP."
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)

@bot.message_handler(commands=['add_rv_vip'])
def cmd_add_rv_vip(message):
    wait_msg = perform_loading(message, "PROCESSING", 0.3)
    if not is_admin(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return
    args = message.text.split()
    if len(args) < 2: 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "USAGE: /add_rv_vip ID_OR_USERNAME")
    target = args[1].lower().replace("@", "")
    if target in db.data.setdefault("vips", []):
        db.data["vips"].remove(target)
        db.save()
        res = f"🗑️ <code>{target}</code> REMOVED FROM VIP LIST."
    else: res = "⚠️ USER NOT FOUND IN VIP LIST."
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)

@bot.message_handler(commands=['set'])
def cmd_set_limit(message):
    wait_msg = perform_loading(message, "PROCESSING", 0.3)
    if not is_admin(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return
    args = message.text.split()
    if len(args) < 3: 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "USAGE: /set UID LIMIT")
    try:
        uid, limit = args[1], int(args[2])
        db.data.setdefault("custom_limits", {})[uid] = limit
        db.save()
        res = f"✅ DAILY USAGE LIMIT FOR <code>{uid}</code> SET TO {limit}."
    except: res = "❌ INVALID FORMAT... USE NUMBERS."
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)

@bot.message_handler(commands=['bot_lock'])
def cmd_bot_lock(message):
    wait_msg = perform_loading(message, "LOCKING BOT", 0.3)
    if not is_admin(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return
    db.data["bot_locked"] = True
    db.save()
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, "🔒 <b>BOT LOCKED SUCCESSFULLY!</b>\nONLY OWNER & ADMINS CAN USE THE BOT NOW.")

@bot.message_handler(commands=['on'])
def cmd_bot_unlock(message):
    wait_msg = perform_loading(message, "UNLOCKING BOT", 0.3)
    if not is_admin(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return
    db.data["bot_locked"] = False
    db.save()
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, "🔓 <b>BOT UNLOCKED SUCCESSFULLY!</b>\nEVERYONE CAN USE THE BOT NORMALLY NOW.")

@bot.message_handler(commands=['leave'])
def cmd_leave(message):
    wait_msg = perform_loading(message, "LEAVING GROUP", 0.3)
    if not is_owner(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ 𝗢𝗡𝗟𝗬 𝗢𝗪𝗡𝗘𝗥 𝗖𝗔𝗡 𝗖𝗛𝗔𝗡𝗚𝗘 𝗧𝗛𝗘 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦...")
    args = message.text.split()
    if len(args) < 2: 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "⚠️ USAGE: `/leave [CHAT_ID]`")
    try:
        chat_id = int(args[1])
        bot.leave_chat(chat_id)
        res = f"✅ LEFT CHAT {chat_id} SUCCESSFULLY."
    except Exception as e: res = f"❌ FAILED TO LEAVE: {e}"
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)

@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    wait_msg = perform_loading(message, "BANNING", 0.3)
    if not is_admin(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ ADMIN/OWNER ONLY.")
    args = message.text.split()
    if len(args) < 2: 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "⚠️ USAGE: `/ban [UID]`")
    try:
        uid = int(args[1])
        if uid not in db.data.setdefault("banned_users", []):
            db.data["banned_users"].append(uid)
            db.save()
        res = f"🚫 USER {uid} HAS BEEN BANNED."
    except: res = "❌ INVALID UID."
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)
@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    wait_msg = perform_loading(message, "UNBANNING", 0.3)
    if not is_admin(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ ADMIN/OWNER ONLY.")
    args = message.text.split()
    if len(args) < 2: 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "⚠️ USAGE: `/unban [UID]`")
    try:
        uid = int(args[1])
        if uid in db.data.setdefault("banned_users", []):
            db.data["banned_users"].remove(uid)
            db.save()
            res = f"✅ USER {uid} HAS BEEN UNBANNED."
        else: res = "⚠️ USER IS NOT BANNED."
    except: res = "❌ INVALID UID."
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, res)

@bot.message_handler(commands=['on_group'])
def cmd_on_group(message):
    wait_msg = perform_loading(message, "ENABLING FORCE JOIN", 0.3)
    if not is_owner(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ 𝗢𝗡𝗟𝗬 𝗢𝗪𝗡𝗘𝗥 𝗖𝗔𝗡 𝗖𝗛𝗔𝗡𝗚𝗘 𝗧𝗛𝗘 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦...")
    args = message.text.split()
    if len(args) < 2: 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "⚠️ USAGE: `/on_group [CHANNEL LINK/USERNAME]`\nEXAMPLE: `/on_group https://t.me/tellygram_like_bot`")
    
    link = args[1]
    channel_id = link
    if link.startswith("https://t.me/"): channel_id = "@" + link.replace("https://t.me/", "").strip("/")
    
    db.data["force_join"] = {"status": True, "channel_id": channel_id, "link": link}
    db.save()
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, f"✅ <b>FORCE JOIN ENABLED!</b>\nUSERS MUST JOIN: {link}")

@bot.message_handler(commands=['off_group'])
def cmd_off_group(message):
    wait_msg = perform_loading(message, "DISABLING FORCE JOIN", 0.3)
    if not is_owner(message.from_user.id): 
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        return bot.reply_to(message, "❌ 𝗢𝗡𝗟𝗬 𝗢𝗪𝗡𝗘𝗥 𝗖𝗔𝗡 𝗖𝗛𝗔𝗡𝗚𝗘 𝗧𝗛𝗘 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦...")
    if "force_join" in db.data:
        db.data["force_join"]["status"] = False
        db.save()
    try: bot.delete_message(message.chat.id, wait_msg.message_id)
    except: pass
    bot.reply_to(message, "✅ <b>FORCE JOIN DISABLED!</b> USERS NO LONGER NEED TO JOIN.")

# ---------- COMMAND MAPPER ----------
CMD_FUNCTIONS = {
    "start": cmd_start,
    "me": show_me,
    "sts": cmd_sts,
    "sts_1": cmd_sts_weekly,
    "sts_2": cmd_sts_monthly,
    "owner": cmd_owner_menu,
    "owner_add": add_sub_owner,
    "owner_rv": rv_sub_owner,
    "owner_list": cmd_owner_list,
    "admin": cmd_admin_menu,
    "admin_rv": rv_admin,
    "setgroup": set_group,
    "group_rv": rv_group,
    "groups": list_groups,
    "add_vip": cmd_add_vip,
    "add_rv_vip": cmd_add_rv_vip,
    "set": cmd_set_limit,
    "api_time": cmd_api_time,
    "off_api": off_api,
    "on_api": on_api,
    "auto_like": cmd_auto_like,
    "auto_off": cmd_auto_off,
    "free_auto": cmd_free_auto,
    "au_like_ti": cmd_au_like_ti,
    "au_like_off": cmd_au_like_off,
    "au_like_list": cmd_au_like_list,
    "like": handle_like,
    "vip_like": handle_vip_like,
    "photo_video_list": list_media,
    "photo": add_media,
    "video": add_media,
    "backup": cmd_backup,
    "restore": cmd_restore,
    "bot_lock": cmd_bot_lock,
    "on": cmd_bot_unlock,
    "setting": cmd_setting,
    "cast": cmd_cast,
    "leave": cmd_leave,
    "ban": cmd_ban,
    "unban": cmd_unban,
    "on_group": cmd_on_group,
    "off_group": cmd_off_group
}

# ---------- BACKGROUND SCHEDULER ----------
def scheduler():
    while True:
        try:
            now_time = time.time()
            if now_time < db.data.get("api_off_until", 0):
                time.sleep(60)
                continue 
                
            now_dhaka = datetime.now(DHAKA_TZ)
            current_date = now_dhaka.strftime("%Y-%m-%d")
            
            # SCHEDULED TIME AUTO LIKES
            scheduled = db.data.get("scheduled_auto", {})
            to_delete = []
            now_ts = now_dhaka.timestamp()
            
            for sched_id, info in list(scheduled.items()):
                if now_ts >= info["trigger_ts"]:
                    try:
                        uid, region = info["uid"], info["region"]
                        # USING VIP LOGIC FOR SCHEDULED ONES TO ENSURE DELIVERY
                        player_name = "N/A"
                        final_after = 0
                        final_before = 0
                        total_added = 0
                        
                        for i in range(1, 11):
                            api_key = str(i)
                            if not db.data.get("api_status", {}).get(api_key, True): continue
                            url = VIP_APIS.get(api_key)
                            if not url: continue
                            
                            try:
                                req = requests.get(url.format(uid=uid, region=region.upper()), timeout=26)
                                res = req.json()
                                if "LikesafterCommand" in res:
                                    player_name = str(res.get('PlayerNickname', player_name)).upper()
                                    after = res.get('LikesafterCommand', 0)
                                    before = res.get('LikesbeforeCommand')
                                    
                                    if before is not None:
                                        added = after - before
                                        if final_before == 0 or before < final_before:
                                            final_before = before
                                    else:
                                        added = 1
                                        if final_before == 0:
                                            final_before = after - added
                                    
                                    final_after = max(final_after, after)
                                    total_added += added
                            except Exception: pass
                        
                        success_msg = (
                            "   <b>SCHEDULED AUTO LIKE SENT</b> \n"
                            "╔═════════════════╗\n"
                            f"👤 <b>𝗣𝗟𝗔𝗬𝗘𝗥</b>  : {player_name}\n"
                            f"🆔 <b>𝗨𝗜𝗗</b>     : <code>{uid}</code>\n"
                            f"🌐 <b>𝗥𝗘𝗚𝗜𝗢𝗡</b>  : {region.upper()}\n"
                            "╚═════════════════╝\n"
                            "╭━━━━━━━━━━━━━━━━━╮\n"
                            f"💝 <b>𝗕𝗘𝗙𝗢𝗥𝗘</b> : <b>{final_before}</b>\n"
                            f"💞 <b>𝗔𝗙𝗧𝗘𝗥</b>    : {final_after}\n"
                            f"➕ <b>𝗔𝗗𝗗𝗘𝗗</b>  : <b>{total_added}</b>\n"
                            "╰━━━━━━━━━━━━━━━━━╯\n\n"
                            "⚡ <b>𝗦𝗧𝗔𝗧𝗨𝗦</b> : <b>𝗔𝗟𝗪𝗔𝗬𝗦 𝗥𝗘𝗔𝗗𝗬 𝗧𝗢 𝗗𝗘𝗟𝗜𝗩𝗘𝗥 𝗚𝗜𝗩𝗘𝗡 𝗟𝗜𝗞𝗘𝗦 💞</b>\n\n"
                            "╔═════════════════╗\n"
                            "    👑  𝗦𝗛𝗔𝗣𝗣𝗡𝗢 𝗖𝗢𝗗𝗘𝗫   👑\n"
                            "╚═════════════════╝"
                        )
                        send_media_msg(info["chat_id"], success_msg, "4", None)
                    except Exception: pass
                    to_delete.append(sched_id)

            for d in to_delete:
                if d in scheduled:
                    del scheduled[d]
            if to_delete:
                db.save()
            
            # FREE DAILY 4 AM AUTO LIKES
            if now_dhaka.hour == 4 and now_dhaka.minute == 0:
                if db.data.get("last_auto_run") != current_date:
                    db.data["last_auto_run"] = current_date
                    db.save()
                    
                    for uid, info in list(db.data.get("free_auto_likes", {}).items()):
                        try:
                            req = requests.get(FREE_API_URL.format(region=info['region'].upper(), uid=uid), timeout=20)
                            res = req.json()
                            if "LikesafterCommand" in res:
                                player_name = str(res.get('PlayerNickname', 'N/A')).upper()
                                after_like = res.get('LikesafterCommand', 0)
                                before_like = res.get('LikesbeforeCommand')
                                if before_like is not None: added_likes = after_like - before_like
                                else: added_likes = 1; before_like = after_like - added_likes
                                
                                success_msg = (
                                    "   <b>FREE AUTO LIKE SUCCESSFULLY SENT</b> \n"
                                    "╔═════════════════╗\n"
                                    f"👤 <b>𝗣𝗟𝗔𝗬𝗘𝗥</b>  : {player_name}\n"
                                    f"🆔 <b>𝗨𝗜𝗗</b>     : <code>{uid}</code>\n"
                                    f"🌐 <b>𝗥𝗘𝗚𝗜𝗢𝗡</b>  : {info['region'].upper()}\n"
                                    "╚═════════════════╝\n"
                                    "╭━━━━━━━━━━━━━━━━━╮\n"
                                    f"💝 <b>𝗕𝗘𝗙𝗢𝗥𝗘</b> : {before_like}\n"
                                    f"💞 <b>𝗔𝗙𝗧𝗘𝗥</b>    : {after_like}\n"
                                    f"➕ <b>𝗔𝗗𝗗𝗘𝗗</b>  : {added_likes}\n"
                                    "╰━━━━━━━━━━━━━━━━━╯\n\n"
                                    "⚡ <b>𝗦𝗧𝗔𝗧𝗨𝗦</b> : <b>𝗔𝗟𝗪𝗔𝗬𝗦 𝗥𝗘𝗔𝗗𝗬 𝗧𝗢 𝗗𝗘𝗟𝗜𝗩𝗘𝗥 𝗚𝗜𝗩𝗘𝗡 𝗟𝗜𝗞𝗘𝗦 💞</b>\n\n"
                                    "╔═════════════════╗\n"
                                    "    👑   JIHADX 𝗖𝗢𝗗𝗘𝗫   👑\n"
                                    "╚═════════════════╝"
                                )
                                send_media_msg(info["chat_id"], success_msg, "4", None)
                            time.sleep(2) 
                        except Exception: 
                            pass
        except Exception: 
            pass
        time.sleep(30)

# ---------- STARTUP ----------
if __name__ == "__main__":
    threading.Thread(target=scheduler, daemon=True).start()
    print("BOT IS ONLINE. ADVANCED PREMIUM VERSION FULLY LOADED...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)