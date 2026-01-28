import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ===================== ENV =====================
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. Railway/Render Variables ga BOT_TOKEN qo‘ying.")

# Ixtiyoriy: bot faqat shu bitta superguruhda ishlasin desangiz, ALLOWED_CHAT_ID ni qo‘ying.
# Supergroup chat_id odatda -100... ko‘rinishida bo‘ladi.
ALLOWED_CHAT_ID = (os.getenv("ALLOWED_CHAT_ID") or "").strip()
ALLOWED_CHAT_ID_INT = int(ALLOWED_CHAT_ID) if ALLOWED_CHAT_ID else None

# Topic (bo‘lim) thread id larni ENV orqali beramiz (ixtiyoriy, lekin tavsiya).
# Buni topish uchun har bir topicda /id deb yozasiz.
# Misol:
# TOPIC_IJARA_ID=123
# TOPIC_ISH_ID=456
# TOPIC_TAXI_ID=789
# TOPIC_VISA_ID=101112
def _get_int_env(name: str) -> Optional[int]:
    v = (os.getenv(name) or "").strip()
    return int(v) if v.isdigit() else None

TOPIC_IDS = {
    "🏠 Uy-joy & Ijara": _get_int_env("TOPIC_IJARA_ID"),
    "💼 Ish & Daromad": _get_int_env("TOPIC_ISH_ID"),
    "🚕 Transport & Taksi": _get_int_env("TOPIC_TAXI_ID"),
    "📄 Hujjatlar & Visa": _get_int_env("TOPIC_VISA_ID"),
    "🛒 Bozor & Narxlar": _get_int_env("TOPIC_BOZOR_ID"),
    "🕋 Ziyorat & Umra": _get_int_env("TOPIC_ZIYORAT_ID"),
    "🌿 Salomatlik": _get_int_env("TOPIC_SALOMAT_ID"),
    "💬 Umumiy savollar": _get_int_env("TOPIC_UMUMIY_ID"),
}

# Agar topic ID topilmagan bo‘lsa, bot baribir yo‘naltiradi (faqat nusxa yubora olmaydi).
COPY_TO_TOPIC = (os.getenv("COPY_TO_TOPIC") or "1").strip()  # "1" bo‘lsa nusxa yuboradi
COPY_TO_TOPIC = COPY_TO_TOPIC not in ("0", "false", "False", "no", "NO")

# ===================== RULES =====================

@dataclass
class TopicRule:
    topic_name: str
    keywords: List[str]

RULES: List[TopicRule] = [
    TopicRule("🏠 Uy-joy & Ijara", ["ijara", "uy", "xonadosh", "xona", "kvartira", "room", "kv"]),
    TopicRule("💼 Ish & Daromad", ["ish", "kuryer", "daromad", "vakansiya", "job", "work", "maosh"]),
    TopicRule("🚕 Transport & Taksi", ["taksi", "careem", "uber", "transport", "bus", "velo", "velosiped"]),
    TopicRule("📄 Hujjatlar & Visa", ["iqoma", "visa", "bank", "karta", "mada", "stc", "sim", "absher"]),
    TopicRule("🛒 Bozor & Narxlar", ["bozor", "narx", "arzon", "market", "haraj", "sotib", "olib-sotish"]),
    TopicRule("🕋 Ziyorat & Umra", ["umra", "ziyorat", "masjid", "nabaviy", "haram", "makkah", "makka", "madina"]),
    TopicRule("🌿 Salomatlik", ["yo'tal", "allergiya", "davo", "toshma", "og'riq", "dor", "tabiiy"]),
]

# ===================== HELPERS =====================

def allowed_chat(update: Update) -> bool:
    if ALLOWED_CHAT_ID_INT is None:
        return True
    return bool(update.effective_chat and update.effective_chat.id == ALLOWED_CHAT_ID_INT)

def detect_topic(text: str) -> Optional[str]:
    t = text.lower()
    for rule in RULES:
        if any(k in t for k in rule.keywords):
            return rule.topic_name
    return None

def user_mention(update: Update) -> str:
    u = update.effective_user
    if not u:
        return "Foydalanuvchi"
    # mention_html works best
    name = (u.full_name or "User").replace("<", "").replace(">", "")
    return f'<a href="tg://user?id={u.id}">{name}</a>'

# ===================== COMMANDS =====================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed_chat(update):
        return
    await update.message.reply_text(
        "🤖 Smart Topic Bot ishlayapti.\n\n"
        "📌 /id — shu joydagi chat_id va topic(thread) id ni ko‘rsatadi.\n"
        "📌 /topics — bot biladigan bo‘limlar va ularning ID holati."
    )

async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed_chat(update):
        return
    msg = update.message
    chat_id = msg.chat_id
    thread_id = msg.message_thread_id  # None bo‘lishi mumkin (topic bo‘lmasa)
    await msg.reply_text(
        f"✅ Chat ID: `{chat_id}`\n"
        f"✅ Topic(Thread) ID: `{thread_id}`\n\n"
        f"Topicda turgan bo‘lsangiz, shu Thread ID ni Railway/Render Variables ga qo‘ying.",
        parse_mode=ParseMode.MARKDOWN,
    )

async def cmd_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed_chat(update):
        return
    lines = ["🧵 **Topiclar holati:**"]
    for k, v in TOPIC_IDS.items():
        lines.append(f"- {k}: `{'OK ' + str(v) if v else 'ID yo‘q'}`")
    lines.append("\n📌 ID olish: har bir topicda `/id` yozing.")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed_chat(update):
        return
    await update.message.reply_text("🧑‍💼 Admin chaqirildi. Savolingizni aniq yozib qoldiring.")

# ===================== MAIN HANDLER =====================

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed_chat(update):
        return

    msg = update.message
    if not msg or not msg.text:
        return

    # Botning o‘zi yozgan xabarlarga javob bermasin
    if msg.from_user and msg.from_user.is_bot:
        return

    detected = detect_topic(msg.text)
    if not detected:
        return  # Hech narsa topilmasa jim turamiz (spam qilmasin)

    current_thread = msg.message_thread_id  # qaysi topicda yozildi
    target_thread = TOPIC_IDS.get(detected)

    # 1) Yo‘naltirish javobi (har doim)
    if target_thread and current_thread != target_thread:
        await msg.reply_text(
            f"📌 Aka, bu savol **{detected}** bo‘limiga to‘g‘ri keladi.\n"
            f"Iltimos, savolingizni shu bo‘limda yozing 👇",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        # To‘g‘ri bo‘limning o‘zida bo‘lsa ham xohlasang “OK” demasak ham bo‘ladi
        return

    # 2) Xabarni to‘g‘ri topicga nusxa qilib yuborish (ixtiyoriy)
    if COPY_TO_TOPIC and target_thread:
        mention = user_mention(update)
        text = msg.text.strip()

        # Bot to‘g‘ri topicga yangi post qilib yuboradi
        await context.bot.send_message(
            chat_id=msg.chat_id,
            message_thread_id=target_thread,
            text=(
                f"🧾 {mention} yozdi (noto‘g‘ri bo‘limdan ko‘chirildi):\n\n"
                f"{text}"
            ),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )

# ===================== RUN =====================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("topics", cmd_topics))
    app.add_handler(CommandHandler("admin", cmd_admin))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    print("🤖 Smart Topic Bot ishga tushdi")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
