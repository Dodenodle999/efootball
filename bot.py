import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = "8640200936:AAGscp850buNxFBHgj2f1vczYiUmfYv_8Hk"
DATA_FILE = "data.json"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# حالة مؤقتة لكل مستخدم: ننتظر منه اسم اللاعب بعد إرسال الصورة
waiting_for_name = {}  # user_id: file_id

# ========= أدوات البيانات =========

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"players": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "players" not in data:
            data["players"] = {}
        return data
    except Exception:
        return {"players": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def now_iraq():
    try:
        tz = ZoneInfo("Asia/Baghdad")
        dt = datetime.now(tz)
    except Exception:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d"), dt.strftime("%I:%M %p")

data = load_data()

# ========= القوائم =========

def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(
        KeyboardButton("➕ إضافة صورة"),
        KeyboardButton("📂 عرض اللاعبين")
    )
    kb.row(
        KeyboardButton("ℹ️ المساعدة")
    )
    return kb

def players_inline_keyboard():
    kb = InlineKeyboardMarkup()
    players = sorted(data["players"].keys(), key=lambda x: x.lower())
    if not players:
        kb.add(InlineKeyboardButton("لا يوجد لاعبون محفوظون", callback_data="noop"))
        return kb

    for name in players:
        count = len(data["players"][name])
        kb.add(InlineKeyboardButton(f"{name} ({count})", callback_data=f"view_player|{name}"))
    return kb

def back_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⬅️ رجوع", callback_data="back_to_players"))
    return kb

# ========= رسائل البداية =========

@bot.message_handler(commands=["start"])
def start(message):
    text = (
        "أهلاً بك 👋\n\n"
        "هذا البوت يحفظ صور نتائج eFootball باستخدام <b>file_id</b> فقط، "
        "مع اسم اللاعب والتاريخ والوقت.\n\n"
        "أرسل صورة النتيجة ثم اكتب اسم اللاعب للحفظ."
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu())

@bot.message_handler(commands=["help"])
def help_cmd(message):
    help_text = (
        "<b>طريقة الاستخدام:</b>\n"
        "1) اضغط <b>➕ إضافة صورة</b>\n"
        "2) أرسل صورة النتيجة\n"
        "3) اكتب اسم اللاعب\n"
        "4) من <b>📂 عرض اللاعبين</b> اختر الاسم لترى الصور\n\n"
        "ملاحظة: الصور لا تُحفظ على الجهاز، بل يُحفظ فقط <b>file_id</b> داخل ملف JSON."
    )
    bot.send_message(message.chat.id, help_text, reply_markup=main_menu())

# ========= زر الإضافة =========

@bot.message_handler(func=lambda m: m.text == "➕ إضافة صورة")
def add_image_button(message):
    bot.send_message(
        message.chat.id,
        "أرسل الآن صورة نتيجة المباراة، وبعدها سأطلب منك اسم اللاعب.",
        reply_markup=main_menu()
    )

# ========= استقبال الصور =========

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    user_id = message.from_user.id
    file_id = message.photo[-1].file_id  # أعلى جودة متاحة
    waiting_for_name[user_id] = file_id

    bot.reply_to(
        message,
        "تم استلام الصورة ✅\n\nالآن اكتب اسم اللاعب الذي تريد حفظها باسمه."
    )

# ========= استقبال الاسم بعد الصورة =========

@bot.message_handler(func=lambda m: m.from_user and m.from_user.id in waiting_for_name and m.content_type == "text")
def save_photo_with_name(message):
    user_id = message.from_user.id
    name = message.text.strip()

    # تجاهل الأوامر أو النصوص الفارغة
    if not name or name.startswith("/"):
        return

    file_id = waiting_for_name.pop(user_id)
    date_str, time_str = now_iraq()

    if name not in data["players"]:
        data["players"][name] = []

    data["players"][name].append({
        "file_id": file_id,
        "date": date_str,
        "time": time_str
    })

    save_data(data)

    bot.reply_to(
        message,
        f"تم الحفظ بنجاح ✅\n\n"
        f"الاسم: <b>{name}</b>\n"
        f"التاريخ: <b>{date_str}</b>\n"
        f"الوقت: <b>{time_str}</b>",
        reply_markup=main_menu()
    )

# ========= عرض اللاعبين =========

@bot.message_handler(func=lambda m: m.text == "📂 عرض اللاعبين")
def show_players(message):
    if not data["players"]:
        bot.send_message(
            message.chat.id,
            "لا يوجد أي لاعب محفوظ حتى الآن.",
            reply_markup=main_menu()
        )
        return

    bot.send_message(
        message.chat.id,
        "اختر اسم اللاعب لعرض صوره:",
        reply_markup=players_inline_keyboard()
    )

# ========= المساعدة =========

@bot.message_handler(func=lambda m: m.text == "ℹ️ المساعدة")
def help_button(message):
    help_cmd(message)

# ========= callbacks =========

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "noop":
        bot.answer_callback_query(call.id)
        return

    if call.data == "back_to_players":
        bot.edit_message_text(
            "اختر اسم اللاعب لعرض صوره:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=players_inline_keyboard()
        )
        bot.answer_callback_query(call.id)
        return

    if call.data.startswith("view_player|"):
        name = call.data.split("|", 1)[1]
        records = data["players"].get(name, [])

        if not records:
            bot.answer_callback_query(call.id, "لا توجد صور لهذا اللاعب")
            return

        bot.answer_callback_query(call.id, f"جاري إرسال صور {name}...")

        # نرسل كل صورة برسالة منفصلة مع التاريخ والوقت
        for idx, record in enumerate(records, start=1):
            caption = (
                f"<b>{name}</b>\n"
                f"📅 {record['date']}\n"
                f"🕒 {record['time']}\n"
                f"#{idx}"
            )
            try:
                bot.send_photo(
                    call.message.chat.id,
                    record["file_id"],
                    caption=caption
                )
            except Exception:
                bot.send_message(
                    call.message.chat.id,
                    f"تعذر إرسال صورة رقم {idx} للاعب {name}."
                )

        # زر رجوع بعد الانتهاء
        bot.send_message(
            call.message.chat.id,
            "انتهى العرض.",
            reply_markup=back_keyboard()
        )

# ========= أي نص آخر =========

@bot.message_handler(content_types=["text"])
def fallback(message):
    # إذا لم يكن في وضع انتظار الاسم، نوجهه للقائمة
    if message.from_user.id not in waiting_for_name:
        bot.send_message(
            message.chat.id,
            "استخدم الأزرار أسفل الشاشة.\nاضغط على <b>➕ إضافة صورة</b> لبدء الحفظ.",
            reply_markup=main_menu()
        )

print("Bot is running...")
bot.infinity_polling(skip_pending=True)