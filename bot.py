import os
import re
import logging
from typing import Dict, List, Optional, Tuple

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
TOPICS: Dict[str, Dict[str, object]] = {
    "Uy-joy & Ijara": {
        "id": 197,
        "keywords": [
            "uy", "uy-joy", "ijara", "ijaraga", "kvartira", "xona", "xonadon", "yotoqxona",
            "hostel", "otel", "arenda", "kira", "depozit", "zalog", "renta",
            "shartnoma", "dogovor", "kommunal", "internet", "wifi",
            "уй", "ижара", "квартира", "аренда", "комната", "общежитие", "снять", "сдаю",
        ],
    },
    "Ish & Daromad": {
        "id": 198,
        "keywords": [
            "ish", "ish bor", "vakansiya", "rezume", "cv", "oylik", "maosh", "daromad",
            "kuryer", "dostavka", "delivery", "part time",
            "иш", "вакансия", "работа", "зарплата", "курьер", "подработка",
        ],
    },
    "Transport & Taksi": {
        "id": 199,
        "keywords": [
            "taksi", "taxi", "uber", "careem", "karim", "bolt", "transport",
            "avtobus", "bus", "metro", "yo'l", "marshrut",
            "такси", "убер", "карим", "автобус", "метро", "транспорт",
        ],
    },
    "Hujjatlar & Visa": {
        "id": 200,
        "keywords": [
            "viza", "visa", "iqoma", "iqama", "pasport", "passport", "hujjat", "dokument",
            "tasrix", "tasrih", "tasreeh", "tashrix",
            "absher", "stc", "sug'urta", "insurance", "muhr", "registratsiya",
            "виза", "иқома", "паспорт", "ҳужжат", "документ", "тасрих", "икама",
        ],
    },
    "Bozor & Narxlar": {
        "id": 201,
        "keywords": [
            "bozor", "narx", "qimmat", "arzon", "chegirma", "skidka", "market", "magazin",
            "sotiladi", "olaman", "kurs", "valyuta", "sar",
            "бозор", "нарх", "скидка", "цена", "рынок", "курс",
        ],
    },
    "Ziyorat & Umra": {
        "id": 202,
        "keywords": [
            "ziyorat", "umra", "haj", "makka", "madina", "rawza", "ravza", "nusuk", "haram",
            "bilet", "aviabilet", "chipta", "reys", "flight",
            "зиёрат", "умра", "хаҗ", "макка", "мадина", "билет", "авиабилет", "рейс",
        ],
    },
    "Salomatlik": {
        "id": 203,
        "keywords": [
            "kasal", "og'riq", "dori", "doktor", "shifokor", "kasalxona", "apteka",
            "allergiya", "isitma", "yo'tal", "bosim",
            "касал", "дори", "доктор", "врач", "аптека", "аллергия", "температура",
        ],
    },
    "Umumiy savollar": {
        "id": 1,
        "keywords": [
            "qanday", "qayerda", "qachon", "yordam", "maslahat", "savol",
            "қандай", "қаерда", "қачон", "ёрдам", "маслаҳат", "савол",
            "как", "где", "когда", "помогите", "вопрос",
        ],
    },
}

ID_TO_NAME = {int(v["id"]): k for k, v in TOPICS.items()}

# ================== COMPILE KEYWORDS ==================
COMPILED: Dict[int, Dict[str, object]] = {}
ALL_PHRASE_KWS: List[Tuple[str, int]] = []

for name, data in TOPICS.items():
    tid = int(data["id"])
    kws = [normalize_text(x) for x in (data["keywords"] or []) if x and normalize_text(x)]

    token_kws = set()
    phrase_kws = []
    for kw in kws:
        if " " in kw or "-" in kw:
            phrase_kws.append(kw)
            ALL_PHRASE_KWS.append((kw, tid))
        else:
            token_kws.add(kw)

    COMPILED[tid] = {"name": name, "token_kws": token_kws, "phrase_kws": phrase_kws}

def allowed_chat(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.id == ALLOWED_CHAT_ID)

def detect_topic_id_if_any(text: str) -> Optional[int]:
    t_norm = normalize_text(text)
    toks = set(tokenize(t_norm))

    for ph, tid in ALL_PHRASE_KWS:
        if ph and ph in t_norm:
            return tid

    for tid, obj in COMPILED.items():
        if obj["token_kws"] & toks:
            return tid

    return None

def build_topic_link(update: Update, topic_id: int) -> str:
    chat = update.effective_chat
    if not chat:
        return ""

    if getattr(chat, "username", None):
        return f"https://t.me/{chat.username}/{topic_id}"

    cid = str(chat.id)
    if cid.startswith("-100"):
        internal = cid[4:]
        return f"https://t.me/c/{internal}/{topic_id}"

    internal = str(abs(chat.id))
    return f"https://t.me/c/{internal}/{topic_id}"

def build_redirect_text(topic_name: str, link: str) -> str:
    # Markdown yo‘q! Shuning uchun ** ishlatmaymiz
    return (
        "Iltimos, bu masalani 👇\n\n"
        f"{topic_name}\n\n"
        "bo‘limiga yozing:\n\n"
        f"{link} 👇"
    )

# ================== HANDLERS ==================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed_chat(update):
        return
    await update.effective_message.reply_text(
        "Assalomu alaykum!\n\n"
        "Bot faqat keyword bo‘lsa ishlaydi.\n"
        "Noto‘g‘ri bo‘limga yozilsa, reply qilib to‘g‘ri bo‘lim linkini beradi.\n"
        "Boshqa payt jim turadi."
    )

async def topics_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed_chat(update):
        return
    lines = ["Topiclar (ID):"]
    for tid, obj in sorted(COMPILED.items(), key=lambda x: x[0]):
        lines.append(f"• {obj['name']} = {tid}")
    await update.effective_message.reply_text("\n".join(lines))

async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not getattr(msg, "text", None):
        return
    if not allowed_chat(update):
        return

    target_topic_id = detect_topic_id_if_any(msg.text)
    if target_topic_id is None:
        return  # JIM

    current_tid = getattr(msg, "message_thread_id", None)
    if current_tid == target_topic_id:
        return  # to‘g‘ri topic -> JIM

    # 1) Copy (xato bo‘lsa ham reply yuboramiz)
    copied_ok = False
    try:
        await context.bot.copy_message(
            chat_id=update.effective_chat.id,
            from_chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            message_thread_id=target_topic_id,
        )
        copied_ok = True
    except Exception:
        log.exception("copy_message error")

    # 2) Reply + link (doim ishlaydi, parse_mode yo‘q)
    topic_name = ID_TO_NAME.get(target_topic_id, "kerakli bo‘lim")
    link = build_topic_link(update, target_topic_id)
    reply_text = build_redirect_text(topic_name, link)

    try:
        await msg.reply_text(reply_text, disable_web_page_preview=True)
    except Exception:
        log.exception("reply_text error")

    log.info("Redirected: from_tid=%s -> to_tid=%s copied=%s", current_tid, target_topic_id, copied_ok)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("topics", topics_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

    log.info("✅ Bot start (faqat bitta guruh, faqat keyword bo'lsa; noto‘g‘ri bo‘limda reply).")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
