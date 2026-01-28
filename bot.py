import os
from dataclasses import dataclass
from typing import List, Optional

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

# Ixtiyoriy: faqat bitta superguruhda ishlasin desangiz (tavsiya).
# Masalan: -1001234567890
ALLOWED_CHAT_ID = (os.getenv("ALLOWED_CHAT_ID") or "").strip()
ALLOWED_CHAT_ID_INT = int(ALLOWED_CHAT_ID) if ALLOWED_CHAT_ID else None

# 1 bo‘lsa — bot noto‘g‘ri topicda yozilgan xabarni to‘g‘ri topicga nusxa qilib yuboradi
# 0 bo‘lsa — faqat yo‘naltiradi (kamroq spam)
COPY_TO_TOPIC = (os.getenv("COPY_TO_TOPIC") or "1").strip().lower() not in ("0", "false", "no")

# ===================== TOPIC IDS (SEN BERGAN) =====================
TOPIC_IDS = {
    "🏠 Uy-joy & Ijara": 5,
    "💼 Ish & Daromad": 6,
    "🚕 Transport & Taksi": 7,
    "📄 Hujjatlar & Visa": 8,
    "🛒 Bozor & Narxlar": 9,
    "🕋 Ziyorat & Umra": 10,
    "🌿 Salomatlik": 11,
    "💬 Umumiy savollar": 1,
}

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

def user_mention_html(update: Update) -> str:
    u = update.effective_user
    if not u:
        return "Foydalanuvchi"
    name = (u.full_name or "User").replace("<", "").replace(">", "")
    return f'<a href="tg://user?id={u.id}">{name}</a>'

# ===================== COMMANDS =====================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed_chat(update):
        return
    await update.message.reply_text(
        "🤖 Smart Topic Bot ishlayapti.\n\n"
        "📌 Savolni noto‘g‘ri bo‘limga yozilsa, bot to‘g‘ri bo‘limni aytadi.\n"
        "📌 /admin — admin chaqirish\n"
        "📌 /topics — bo‘limlar ro‘yxati"
    )

async def cmd_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed_chat(update):
        return
    lines = ["🧵 **Topiclar (Thread ID):**"]
    for k, v in TOPIC_IDS.items():
        lines.append(f"- {k}: `{v}`")
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

    # botning o‘zi yozgan xabarlarga javob bermasin
    if msg.from_user and msg.from_user.is_bot:
        return

    detected = detect_topic(msg.text)
    if not detected:
        return  # topilmasa jim turadi

    current_thread = msg.message_thread_id  # yozilgan topic
    target_thread = TOPIC_IDS.get(detected)

    # Agar topic yo‘q bo‘lsa (teoretik), umumiyga yo‘naltiramiz
    if not target_thread:
        target_thread = TOPIC_IDS.get("💬 Umumiy savollar")

    # Noto‘g‘ri bo‘limda bo‘lsa yo‘naltir
    if current_thread != target_thread:
        await msg.reply_text(
            f"📌 Aka, bu savol **{detected}** bo‘limiga to‘g‘ri keladi.\n"
            f"Iltimos, savolingizni shu bo‘limda yozing 👇",
            parse_mode=ParseMode.MARKDOWN,
        )

        # Xabarni to‘g‘ri topicga nusxa qilib yuborish
        if COPY_TO_TOPIC:
            mention = user_mention_html(update)
            text = msg.text.strip()

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
    app.add_handler(CommandHandler("topics", cmd_topics))
    app.add_handler(CommandHandler("admin", cmd_admin))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    print("🤖 Smart Topic Bot ishga tushdi")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
