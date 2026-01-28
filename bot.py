import os
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID", "0"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. Railway Variables ga BOT_TOKEN qo‘ying.")

# ===== TOPIC ID LAR =====
TOPICS = {
    "Uy-joy & Ijara": {
        "id": 5,
        "keywords": ["uy", "ijara", "kvartira", "xonadosh", "room"]
    },
    "Ish & Daromad": {
        "id": 6,
        "keywords": ["ish", "job", "work", "daromad", "kuryer"]
    },
    "Transport & Taksi": {
        "id": 7,
        "keywords": ["taksi", "uber", "careem", "transport", "velo"]
    },
    "Hujjatlar & Visa": {
        "id": 8,
        "keywords": ["iqoma", "visa", "bank", "karta", "stc"]
    },
    "Bozor & Narxlar": {
        "id": 9,
        "keywords": ["narx", "bozor", "qimmat", "arzon"]
    },
    "Ziyorat & Umra": {
        "id": 10,
        "keywords": ["umra", "ziyorat", "madina", "makka"]
    },
    "Salomatlik": {
        "id": 11,
        "keywords": ["kasal", "doktor", "dori", "salomatlik"]
    },
    "Umumiy savollar": {
        "id": 12,
        "keywords": []
    }
}

# ===== ASOSIY LOGIKA =====
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    text = update.message.text.lower()

    for name, data in TOPICS.items():
        if any(k in text for k in data["keywords"]):
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
                message_thread_id=data["id"]
            )
            await update.message.reply_text(
                f"📌 Savolingiz **{name}** bo‘limiga ko‘chirildi.\n"
                f"Iltimos, shu bo‘limda davom ettiring 🙌"
            )
            return

    # Agar hech biriga tushmasa → Umumiy savollar
    await context.bot.copy_message(
        chat_id=update.effective_chat.id,
        from_chat_id=update.effective_chat.id,
        message_id=update.message.message_id,
        message_thread_id=12
    )
    await update.message.reply_text(
        "📌 Savolingiz **Umumiy savollar** bo‘limiga joylandi."
    )

# ===== START =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))
    print("🤖 Saudiya Smart Topic Bot ishga tushdi")
    app.run_polling()

if __name__ == "__main__":
    main()
