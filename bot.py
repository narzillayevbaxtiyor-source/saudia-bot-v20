import os
import re
import logging
from typing import Dict, List

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== ENV ==================
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
ALLOWED_CHAT_ID = int((os.getenv("ALLOWED_CHAT_ID") or "0").strip() or "0")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. Railway Variables ga BOT_TOKEN qo'ying.")
if not ALLOWED_CHAT_ID:
    raise RuntimeError("ALLOWED_CHAT_ID topilmadi. Railway Variables ga ALLOWED_CHAT_ID qo'ying.")

# ================== LOGGING ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("saudiya-topic-bot")

# ================== TEXT NORMALIZE ==================
_SPLIT_RE = re.compile(r"[^\w'’`\-]+", flags=re.UNICODE)

def normalize_text(s: str) -> str:
    s = (s or "").lower().strip()
    s = s.replace("’", "'").replace("`", "'")
    s = re.sub(r"\s+", " ", s)
    return s

def tokenize(s: str) -> List[str]:
    parts = _SPLIT_RE.split(normalize_text(s))
    return [p for p in parts if p]

# ================== TOPICS + KEYWORDS ==================
# Topic ID lar (siz bergan):
# Uy-joy & Ijara = 5
# Ish & Daromad = 6
# Transport & Taksi = 7
# Hujjatlar & Visa = 8
# Bozor & Narxlar = 9
# Ziyorat & Umra = 10
# Salomatlik = 11
# Umumiy savollar = 1

TOPICS: Dict[str, Dict[str, object]] = {
    "Uy-joy & Ijara": {
        "id": 5,
        "keywords": [
            "uy", "uy-joy", "ijara", "ijaraga", "kvartira", "xona", "xonadon", "yotoqxona",
            "hostel", "otel", "arenda", "kira", "depozit", "zalog", "renta",
            "shartnoma", "dogovor", "kommunal", "internet", "wifi",
            # krill + rus
            "уй", "ижара", "квартира", "аренда", "комната", "общежитие", "снять", "сдаю",
        ],
    },
    "Ish & Daromad": {
        "id": 6,
        "keywords": [
            "ish", "vakansiya", "rezume", "cv", "oylik", "maosh", "daromad", "kuryer",
            # krill + rus
            "иш", "вакансия", "работа", "зарплата", "курьер",
        ],
    },
    "Transport & Taksi": {
        "id": 7,
        "keywords": [
            "taksi", "taxi", "uber", "careem", "karim", "transport", "avtobus", "bus", "metro",
            # krill + rus
            "такси", "убер", "карим", "автобус", "метро",
        ],
    },
    "Hujjatlar & Visa": {
        "id": 8,
        "keywords": [
            "viza", "visa", "iqoma", "iqama", "pasport", "passport", "hujjat", "dokument",
            "tasrix", "tasrih", "tasreeh", "tashrix",
            "absher", "stc", "sug'urta",
            # krill + rus
            "виза", "иқома", "паспорт", "ҳужжат", "документ", "тасрих", "икама",
        ],
    },
    "Bozor & Narxlar": {
        "id": 9,
        "keywords": [
            "bozor", "narx", "qimmat", "arzon", "chegirma", "skidka", "market", "magazin",
            # krill + rus
            "бозор", "нарх", "скидка", "цена", "рынок",
        ],
    },
    "Ziyorat & Umra": {
        "id": 10,
        "keywords": [
            "ziyorat", "umra", "haj", "makka", "madina", "rawza", "ravza", "nusuk", "haram",
            "bilet", "aviabilet", "chipta", "reys", "flight",
            # krill + rus
            "зиёрат", "умра", "хаҗ", "макка", "мадина", "билет", "авиабилет", "рейс",
        ],
    },
    "Salomatlik": {
        "id": 11,
        "keywords": [
            "kasal", "og'riq", "dori", "doktor", "shifokor", "kasalxona", "apteka",
            "allergiya", "isitma", "yo'tal",
            # krill + rus
            "касал", "дори", "доктор", "врач", "аптека", "аллергия",
        ],
    },
}

ID_TO_NAME = {int(v["id"]): k for k, v in TOPICS.items()}

# ================== COMPILE KEYWORDS ==================
# token match + phrase match
COMPILED: Dict[int, Dict[str, object]] = {}  # topic_id -> {"name":..., "token_kws":set, "phrase_kws":list}
ALL_TOKEN_KWS = set()
ALL_PHRASE_KWS = []

for name, data in TOPICS.items():
    tid = int(data["id"])
    kws = [normalize_text(x) for x in data["keywords"] if x and normalize_text(x)]

    token_kws = set()
    phrase_kws = []
    for kw in kws:
        if " " in kw or "-" in kw:
            phrase_kws.append(kw)
            ALL_PHRASE_KWS.append((kw, tid))
        else:
            token_kws.add(kw)
            ALL_TOKEN_KWS.add(kw)

    COMPILED[tid] = {"name": name, "token_kws": token_kws, "phrase_kws": phrase_kws}

def allowed_chat(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.id == ALLOWED_CHAT_ID)

def detect_topic_id_if_any(text: str) -> int | None:
    """
    Faqat keyword bo'lsa topic qaytaradi.
    Keyword bo'lmasa None (bot jim turadi).
    """
    t_norm = normalize_text(text)
    toks = set(tokenize(t_norm))

    # phrase match
    for ph, tid in ALL_PHRASE_KWS:
        if ph in t_norm:
            return tid

    # token match
    for tid, obj in COMPILED.items():
        if obj["token_kws"] & toks:
            return tid

    return None

def build_topic_link(update: Update, topic_id: int) -> str:
    chat = update.effective_chat
    if not chat:
        return ""

    # Public group (username bor)
    if getattr(chat, "username", None):
        return f"https://t.me/{chat.username}/{topic_id}"

    # Private/supergroup: -100123... -> t.me/c/123.../topic
    cid = str(chat.id)
    if cid.startswith("-100"):
        internal = cid[4:]
        return f"https://t.me/c/{internal}/{topic_id}"

    internal = str(abs(chat.id))
    return f"https://t.me/c/{internal}/{topic_id}"

# ================== HANDLERS ==================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed_chat(update):
        return
    await update.effective_message.reply_text(
        "👋 Assalomu alaykum!\n\n"
        "Kalit so‘zlar bo‘yicha noto‘g‘ri bo‘limga yozilsa, bot yo‘naltiradi.\n"
        "Boshqa payt jim turadi."
    )

async def topics_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed_chat(update):
        return
    lines = ["📌 Topiclar (ID):"]
    for tid, obj in sorted(COMPILED.items(), key=lambda x: x[0]):
        lines.append(f"• {obj['name']} = {tid}")
    await update.effective_message.reply_text("\n".join(lines))

async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not getattr(msg, "text", None):
        return
    if not allowed_chat(update):
        return

    text = msg.text

    # 0) Faqat keyword bo'lsa ishlaymiz; keyword bo'lmasa -> JIM
    target_topic_id = detect_topic_id_if_any(text)
    if target_topic_id is None:
        return

    current_tid = getattr(msg, "message_thread_id", None)

    # 1) Agar user to'g'ri topic ichida yozgan bo'lsa -> JIM
    if current_tid == target_topic_id:
        return

    # 2) Noto'g'ri topicda yozgan bo'lsa -> ko'chiramiz
    try:
        await context.bot.copy_message(
            chat_id=update.effective_chat.id,
            from_chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            message_thread_id=target_topic_id,
        )
    except Exception:
        log.exception("copy_message error")
        return

    # 3) Va faqat shu holatda reply + link
    topic_name = ID_TO_NAME.get(target_topic_id, "kerakli bo‘lim")
    link = build_topic_link(update, target_topic_id)

    reply_text = (
        "Iltimos, bu masalani 👇\n\n"
        f"**{topic_name}**\n\n"
        "bo‘limiga yozing:\n\n"
        f"{link} 👇"
    )

    await msg.reply_text(reply_text, parse_mode="Markdown", disable_web_page_preview=True)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("topics", topics_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

    log.info("✅ Saudiya Smart Topic Bot ishga tushdi (faqat bitta guruh, faqat keyword bo'lsa).")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
