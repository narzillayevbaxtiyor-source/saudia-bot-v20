import os
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
    CommandHandler,
)

# ====== ENV ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID", "0"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN yo‘q")

# ====== TOPICLAR ======
TOPICS = {
    "Uy-joy & Ijara": {
        "id": 5,
        "keywords": ["uy", "ijara", "kvartira", "xona", "room"],
    },
    "Ish & Daromad": {
        "id": 6,
        "keywords": ["ish", "job", "work", "daromad"],
    },
    "Transport & Taksi": {
        "id": 7,
        "keywords": ["taksi", "uber", "careem", "transport"],
    },
    "Hujjatlar & Visa": {
        "id": 8,
        "keywords": ["iqoma", "visa", "bank", "karta"],
    },
    "Bozor & Narxlar": {
        "id": 9,
        "keywords": ["narx", "bozor", "qimmat", "arzon"],
    },
    "Ziyorat & Umra": {
        "id": 10,
        "keywords": ["umra", "ziyorat", "madina", "makka"],
    },
    "Salomatlik": {
        "id": 11,
        "keywords": ["kasal", "doktor", "dori"],
    },
    "Umumiy savollar": {
        "id": 12,
        "keywords": [],
    },
}

# ====== /start ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    await update.message.reply_text(
        "👋 Assalomu alaykum!\n\n"
        "Savolingizni yozing — bot uni avtomatik ravishda to‘g‘ri bo‘limga joylaydi 🤖"
    )

# ====== ASOSIY ROUTER ======
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    # ❗ faqat ruxsat berilgan supergroupda ishlaydi, lekin jim
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    text = update.message.text.lower()

    for name, data in TOPICS.items():
        if any(k in text for k in data["keywords"]):
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
                message_thread_id=data["id"],
            )
            await update.message.reply_text(
                f"✅ Savolingiz **{name}** bo‘limiga joylandi."
            )
            return

    # hech biriga tushmasa → Umumiy
    await context.bot.copy_message(
        chat_id=update.effective_chat.id,
        from_chat_id=update.effective_chat.id,
        message_id=update.message.message_id,
        message_thread_id=12,
    )

    await update.message.reply_text(
        "ℹ️ Savolingiz **Umumiy savollar** bo‘limiga joylandi."
    )

# ====== MAIN ======
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

    print("🤖 Saudiya Smart Topic Bot ishga tushdi")
    app.run_polling()

if __name__ == "__main__":
    main()
