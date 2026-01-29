import os
import re
import time
import logging
from typing import Dict, List

from telegram import Update
from telegram.error import Conflict, NetworkError, TimedOut
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

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
    s = normalize_text(s)
    parts = _SPLIT_RE.split(s)
    return [p for p in parts if p]

# ================== TOPICS + KEYWORDS ==================
TOPICS: Dict[str, Dict[str, object]] = {
    "Uy-joy & Ijara": {
        "id": 5,
        "keywords": [
            "uy", "uy-joy", "ijara", "ijaraga", "kvartira", "xona", "xonadon", "yotoqxona",
            "hostel", "otel", "arenda", "kira", "depozit", "zalog", "renta",
            "kommunal", "komunal", "internet", "wifi", "shartnoma", "dogovor",
            # krill
            "уй", "уй-жой", "ижара", "ижарага", "квартира", "хона", "хонaдон", "ётоқхона",
            "аренда", "кира", "депозит", "залог", "шартнома", "договор",
            # rus
            "квартира", "аренда", "снять", "сдаю", "комната", "общежитие", "залог",
        ],
    },
    "Ish & Daromad": {
        "id": 6,
        "keywords": [
            "ish", "ish bor", "ish topish", "vakansiya", "rezume", "cv",
            "oylik", "maosh", "daromad", "kuryer", "dostavka", "delivery",
            # krill
            "иш", "вакансия", "резюме", "ойлик", "маош", "даромад", "курьер", "доставка",
            # rus
            "работа", "вакансия", "подработка", "зарплата", "курьер", "доставка",
        ],
    },
    "Transport & Taksi": {
        "id": 7,
        "keywords": [
            "taksi", "taxi", "uber", "careem", "karim", "bolt",
            "transport", "avtobus", "bus", "metro",
            "yo'l", "marshrut", "bekat", "stansiya",
            # krill
            "такси", "убер", "карим", "транспорт", "автобус", "метро", "йўл", "маршрут",
            # rus
            "такси", "uber", "careem", "автобус", "метро", "штраф",
        ],
    },
    "Hujjatlar & Visa": {
        "id": 8,
        "keywords": [
            "viza", "visa", "iqoma", "iqama", "pasport", "passport", "hujjat", "dokument",
            # tasrix variantlari
            "tasrix", "tasrih", "tasreh", "tasreeh", "tashrix", "tashrih",
            "muhr", "registratsiya", "sug'urta", "insurance", "kafil",
            # krill
            "виза", "виса", "иқома", "паспорт", "ҳужжат", "документ",
            "тасрих", "ташрих", "муҳр", "регистрация", "суғурта", "кафил",
            # rus
            "виза", "паспорт", "икама", "документы", "страховка", "регистрация",
        ],
    },
    "Bozor & Narxlar": {
        "id": 9,
        "keywords": [
            "bozor", "narx", "qimmat", "arzon", "chegirma", "skidka",
            "do'kon", "market", "magazin", "kurs", "valyuta", "sar", "riyal",
            # krill
            "бозор", "нарх", "қиммат", "арзон", "чегирма", "дўкон", "маркет", "курс",
            # rus
            "цена", "рынок", "дешево", "дорого", "скидка", "магазин",
        ],
    },
    "Ziyorat & Umra": {
        "id": 10,
        "keywords": [
            "ziyorat", "umra", "haj", "makka", "madina", "rawza", "ravza", "nusuk", "haram",
            # bilet/chipta
            "bilet", "aviabilet", "chipta", "reys", "flight",
            # krill
            "зиёрат", "умра", "ҳаҗ", "макка", "мадина", "равза", "ҳарам",
            "билет", "авиабилет", "чипта", "рейс",
            # rus
            "умра", "хадж", "мекка", "медина", "билет", "авиабилет", "рейс",
        ],
    },
    "Salomatlik": {
        "id": 11,
        "keywords": [
            "kasal", "og'riq", "dori", "doktor", "shifokor", "kasalxona", "apteka",
            "allergiya", "isitma", "yo'tal",
            # krill
            "касал", "оғриқ", "дори", "доктор", "шифокор", "касалхона", "аптека",
            # rus
            "врач", "больница", "аптека", "лекарство", "аллергия",
        ],
    },
    "Umumiy savollar": {
        "id": 1,
        "keywords": [
            "savol", "qanday", "qayerda", "qachon", "yordam", "maslahat",
            "савол", "қандай", "қаерда", "қачон", "ёрдам",
            "вопрос", "как", "где", "когда", "помогите",
        ],
    },
}

DEFAULT_TOPIC_ID = int(TOPICS["Umumiy savollar"]["id"])

# ================== KEYWORD COMPILE ==================
COMPILED: Dict[str, Dict[str, object]] = {}
ID_TO_NAME: Dict[int, str] = {}

for name, data in TOPICS.items():
    tid = int(data["id"])
    ID_TO_NAME[tid] = name

    kws = [normalize_text(x) for x in data["keywords"] if x and normalize_text(x)]
    token_kws = set()
    phrase_kws = []
    for kw in kws:
        if " " in kw or "-" in kw:
            phrase_kws.append(kw)
        else:
            token_kws.add(kw)

    COMPILED[name] = {"id": tid, "token_kws": token_kws, "phrase_kws": phrase_kws}

# ================== ACCESS ==================
def allowed_chat(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.id == ALLOWED_CHAT_ID)

# ================== TOPIC MATCH ==================
def find_topic_id(text: str) -> int:
    t_norm = normalize_text(text)
    toks = set(tokenize(t_norm))

    for _, data in COMPILED.items():
        for ph in data["phrase_kws"]:
            if ph in t_norm:
                return int(data["id"])
        if data["token_kws"] & toks:
            return int(data["id"])

    return DEFAULT_TOPIC_ID

# ================== TOPIC LINK BUILDER ==================
def build_topic_link(update: Update, topic_id: int) -> str:
    chat = update.effective_chat
    if not chat:
        return ""

    # Public group bo'lsa (username bor) → https://t.me/<username>/<topic_id>
    if getattr(chat, "username", None):
        return f"https://t.me/{chat.username}/{topic_id}"

    # Private/supergroup bo'lsa → https://t.me/c/<internal_id>/<topic_id>
    # chat.id odatda: -1001234567890 (supergroup)
    cid = str(chat.id)
    if cid.startswith("-100"):
        internal = cid[4:]  # "-100" ni olib tashlaymiz
        return f"https://t.me/c/{internal}/{topic_id}"

    # fallback
    internal = str(abs(chat.id))
    return f"https://t.me/c/{internal}/{topic_id}"

# ================== HANDLERS ==================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed_chat(update):
        return
    await update.effective_message.reply_text(
        "👋 Assalomu alaykum!\n\nSavolingizni yozing — bot uni avtomatik ravishda to‘g‘ri bo‘lim (topic)ga ko‘chiradi 🤖"
    )

async def topics_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed_chat(update):
        return
    lines = ["📌 Topiclar ro‘yxati (ID):"]
    for name, data in COMPILED.items():
        lines.append(f"• {name} = {data['id']}")
    await update.effective_message.reply_text("\n".join(lines))

async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not getattr(msg, "text", None):
        return
    if not allowed_chat(update):
        return

    text = msg.text
    topic_id = find_topic_id(text)

    current_tid = getattr(msg, "message_thread_id", None)

    # Agar allaqachon to'g'ri topicda bo'lsa – jim
    if current_tid == topic_id:
        return

    # 1) Xabarni to'g'ri topicga ko'chiramiz
    try:
        await context.bot.copy_message(
            chat_id=update.effective_chat.id,
            from_chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            message_thread_id=topic_id,
        )
    except Exception:
        log.exception("copy_message error")
        return

    # 2) Userga reply qilib to'g'ri bo'lim linkini yuboramiz
    try:
        topic_name = ID_TO_NAME.get(topic_id, "kerakli bo‘lim")
        link = build_topic_link(update, topic_id)

        # link bo'lmasa ham matn chiqsin
        if link:
            reply_text = (
    "Iltimos, bu masalani 👇\n\n"
    f"**{topic_name}**\n\n"
    "bo‘limiga yozing:\n\n"
    f"{link}"
            )
        else:
            reply_text = f" Iltimos, bu masalani **{topic_name}** bo‘limiga yozing."

        # HTML ishlatsak bold oson bo'ladi
        await msg.reply_text(reply_text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception:
        log.exception("reply with link error")

# ================== BUILD APP ==================
def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler(["start"], start_cmd))
    app.add_handler(CommandHandler(["topics"], topics_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))
    return app

# ================== MAIN (STABLE) ==================
def main():
    log.info("✅ Bot start (faqat bitta guruh). ALLOWED_CHAT_ID=%s", ALLOWED_CHAT_ID)

    while True:
        try:
            app = build_app()
            app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
        except Conflict:
            log.warning("⚠️ Conflict: boshqa instans polling qilyapti. 15s kutaman...")
            time.sleep(15)
        except (TimedOut, NetworkError) as e:
            log.warning("⚠️ Network/Timeout: %s. 10s kutaman...", e)
            time.sleep(10)
        except Exception as e:
            log.exception("❌ Kutilmagan xato: %s. 10s kutaman...", e)
            time.sleep(10)

if __name__ == "__main__":
    main()
