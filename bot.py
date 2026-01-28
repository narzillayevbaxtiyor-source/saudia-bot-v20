import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID", "0"))

TOPICS = {
    "uy": 5,
    "ijara": 5,
    "ish": 6,
    "daromad": 6,
    "taksi": 7,
    "transport": 7,
    "visa": 8,
    "hujjat": 8,
    "bozor": 9,
    "narx": 9,
    "umra": 10,
    "ziyorat": 10,
    "salomat": 11,
    "shifokor": 11,
}

# ============================================

logging.basicConfig(level=logging.INFO)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

# =============== HANDLERS ===================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Saudiya Smart Bot ishga tushdi")

async def route_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    if ALLOWED_CHAT_ID and msg.chat.id != ALLOWED_CHAT_ID:
        return

    text = msg.text.lower()

    for keyword, topic_id in TOPICS.items():
        if keyword in text:
            await context.bot.send_message(
                chat_id=msg.chat.id,
                text=f"📌 Savolingiz shu bo‘limga mos:\n➡️ Topic ID: {topic_id}",
                message_thread_id=topic_id
            )
            return

    await msg.reply_text(
        "❓ Savolingiz aniq bo‘limga tushmadi.\n"
        "Iltimos, aniqroq yozing yoki umumiy bo‘limga yozing."
    )

# ================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_message))

    app.run_polling()

if __name__ == "__main__":
    main()
