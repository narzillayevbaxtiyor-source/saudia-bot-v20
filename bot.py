import os
import re
import time
import logging
from typing import Dict, List, Tuple

from telegram import Update
from telegram.error import Conflict, NetworkError, TimedOut
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
    s = normalize_text(s)
    parts = _SPLIT_RE.split(s)
    return [p for p in parts if p]

# ================== TOPICS + KEYWORDS ==================
# Topic ID lar:
# Uy-joy & Ijara = 5
# Ish & Daromad = 6
# Transport & Taksi = 7
# Hujjatlar & Visa = 8
# Bozor & Narxlar = 9
# Ziyorat & Umra = 10
# Salomatlik = 11
# Umumiy savollar = 12

TOPICS: Dict[str, Dict[str, object]] = {
    "Uy-joy & Ijara": {
        "id": 5,
        "keywords": [
            # --- UY / IJARA (lotin)
            "uy", "uy-joy", "ijara", "ijaraga", "ijara uy", "uy topish", "uy qidiryapman",
            "kvartira", "kvartiraga", "xona", "xonadon", "yotoqxona", "hostel", "otel",
            "arenda", "arendaga", "kira", "depozit", "zalog", "renta",
            "shartnoma", "dogovor", "kelishuv",
            "kommunal", "komunal", "elektr", "svet", "gaz", "suv", "internet", "wifi",
            "mebel", "mebellik", "konditsioner", "konditsaner", "klimat",
            "ko'chib o'tish", "ko'chish", "manzil", "lokatsiya",
            # --- KRIL (uz)
            "уй", "уй-жой", "ижара", "ижарага", "ижара уй", "уй топиш", "уй қидиряпман",
            "квартира", "хона", "хонaдон", "ётоқхона", "хостел", "отель",
            "аренда", "кира", "депозит", "залог",
            "шартнома", "договор", "келишув",
            "коммунал", "электр", "свет", "газ", "сув", "интернет", "вайфай",
            # --- RUS
            "квартира", "аренда", "снять", "сдаю", "сдам", "комната", "общежитие",
            "залог", "договор", "коммуналка", "интернет", "wi-fi",
        ],
    },
    "Ish & Daromad": {
        "id": 6,
        "keywords": [
            # lotin
            "ish", "ish bor", "ish topish", "vakansiya", "rezume", "cv",
            "oylik", "maosh", "daromad", "ish haqqi", "stavka", "part time", "full time",
            "kuryer", "dostavka", "delivery", "haydovchi", "operator", "sotuvchi",
            "usta", "shogird", "ishchi",
            # kril
            "иш", "иш бор", "иш топиш", "вакансия", "резюме",
            "ойлик", "маош", "даромад", "курьер", "доставка", "ҳайдовчи",
            # rus
            "работа", "вакансия", "подработка", "зарплата", "курьер", "доставка",
            "водитель", "продавец",
        ],
    },
    "Transport & Taksi": {
        "id": 7,
        "keywords": [
            # taksi (lotin)
            "taksi", "taxi", "uber", "careem", "karim", "bolt",
            "transport", "avtobus", "bus", "metro", "poezd", "train",
            "yo'l", "marshrut", "bekat", "stansiya",
            "velosiped", "skuter", "mashina", "avto", "benzin", "parkovka", "jarima",
            "gps", "lokatsiya", "navigatsiya",
            # kril
            "такси", "убер", "карим", "транспорт", "автобус", "метро",
            "йўл", "маршрут", "бекат", "станция",
            "велосипед", "скутер", "машина", "бензин", "парковка", "жарима",
            # rus
            "такси", "uber", "careem", "автобус", "метро", "штраф", "парковка",
        ],
    },
    "Hujjatlar & Visa": {
        "id": 8,
        "keywords": [
            # visa/iqoma (lotin)
            "viza", "visa", "iqoma", "iqama", "паспорт",  # pasport so'zi ba'zan rus klaviaturada
            "pasport", "passport", "hujjat", "dokument", "document",
            "tasrix", "tasrih", "tasreh", "tasreeh", "tashrix", "tashrih",
            "muhr", "registratsiya", "ro'yxat", "registration",
            "sug'urta", "insurance", "muddat", "muddati", "kafolat", "kafil",
            "anketa", "biometrik", "fingerprint",
            "стс", "stc", "absher", "abshar", "absher",  # ko‘p so‘raladi
            # kril (uz)
            "виза", "виса", "иқома", "паспорт", "ҳужжат", "документ",
            "тасрих", "ташрих", "мухр", "муҳр", "регистрация", "рўйхат",
            "суғурта", "муддат", "кафил", "анкета", "биометрик",
            # rus
            "виза", "паспорт", "икама", "документы", "страховка", "регистрация",
            "разрешение", "tasreeh",
        ],
    },
    "Bozor & Narxlar": {
        "id": 9,
        "keywords": [
            # lotin
            "bozor", "narx", "qimmat", "arzon", "chegirma", "skidka",
            "do'kon", "market", "magazin", "sotib olish", "sotiladi", "olaman",
            "kurs", "valyuta", "sar", "riyal", "riyo'l",
            # kril
            "бозор", "нарх", "қиммат", "арзон", "чегирма", "дўкон", "маркет",
            "магазин", "курс", "валюта", "риал",
            # rus
            "цена", "рынок", "дешево", "дорого", "скидка", "магазин", "купить",
        ],
    },
    "Ziyorat & Umra": {
        "id": 10,
        "keywords": [
            # lotin
            "ziyorat", "umra", "haj", "makka", "madina", "masjid", "rawza", "ravza",
            "nusuk", "haram", "tawaf", "tavof", "sa'y", "say", "ihram", "manosik",
            "bilet", "avia bilet", "aviabilet", "reys", "flight", "chipta", "chipta olish",
            # kril
            "зиёрат", "умра", "ҳаҗ", "макка", "мадина", "масжид", "равза", "ҳарам",
            "тавoф", "саъй", "иҳром", "маносик",
            "билет", "авиабилет", "рейс", "чипта",
            # rus
            "умра", "хадж", "мекка", "медина", "таваф", "саи", "ихрам",
            "билет", "авиабилет", "рейс", "самолет",
        ],
    },
    "Salomatlik": {
        "id": 11,
        "keywords": [
            # lotin
            "kasal", "og'riq", "dori", "doktor", "shifokor", "kasalxona", "apteka",
            "allergiya", "isitma", "yo'tal", "bosim", "tomoq", "tish", "tez yordam",
            # kril
            "касал", "оғриқ", "дори", "доктор", "шифокор", "касалхона", "аптека",
            "аллергия", "иситма", "йўтал", "босим", "томоқ", "тиш",
            # rus
            "врач", "больница", "аптека", "лекарство", "аллергия", "температура",
        ],
    },
    "Umumiy savollar": {
        "id": 12,
        "keywords": [
            # lotin
            "savol", "qanday", "qayerda", "qachon", "yordam", "maslahat", "bilasizmi",
            # kril
            "савол", "қандай", "қаерда", "қачон", "ёрдам", "маслаҳат",
            # rus
            "вопрос", "как", "где", "когда", "помогите",
        ],
    },
}

DEFAULT_TOPIC_ID = int(TOPICS["Umumiy savollar"]["id"])

# Precompute token keywords vs phrase keywords
# - token_keywords: tek so'zlar (token ichida)
# - phrase_keywords: bo'shliq yoki '-' bo'lgan iboralar (matn ichida)
COMPILED: Dict[str, Dict[str, object]] = {}
for name, data in TOPICS.items():
    kws = [normalize_text(x) for x in data["keywords"] if x and normalize_text(x)]
    token_kws = set()
    phrase_kws = []
    for kw in kws:
        if " " in kw or "-" in kw:
            phrase_kws.append(kw)
        else:
            token_kws.add(kw)
    COMPILED[name] = {
        "id": int(data["id"]),
        "token_kws": token_kws,
        "phrase_kws": phrase_kws,
    }

# ================== ACCESS ==================
def allowed_chat(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.id == ALLOWED_CHAT_ID)

# ================== TOPIC MATCH ==================
def find_topic_id(text: str) -> int:
    t_norm = normalize_text(text)
    toks = set(tokenize(t_norm))

    for name, data in COMPILED.items():
        # phrase match
        for ph in data["phrase_kws"]:
            if ph in t_norm:
                return int(data["id"])
        # token match
        if data["token_kws"] & toks:
            return int(data["id"])

    return DEFAULT_TOPIC_ID

# ================== HANDLERS ==================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed_chat(update):
        return
    await update.effective_message.reply_text(
        "👋 Assalomu alaykum!\n\n"
        "Savolingizni yozing — bot uni avtomatik ravishda to‘g‘ri bo‘lim (topic)ga ko‘chiradi 🤖"
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

    # Agar xabar allaqachon shu topic ichida bo'lsa — hech narsa qilmaymiz
    if getattr(msg, "message_thread_id", None) == topic_id:
        return

    try:
        await context.bot.copy_message(
            chat_id=update.effective_chat.id,
            from_chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            message_thread_id=topic_id,
        )
    except Exception:
        log.exception("copy_message error")

# ================== BUILD APP ==================
def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler(["start"], start_cmd))
    app.add_handler(CommandHandler(["topics"], topics_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))
    return app

# ================== MAIN (STABLE) ==================
def main():
    log.info("✅ Saudiya Smart Topic Bot start (faqat bitta guruh uchun). ALLOWED_CHAT_ID=%s", ALLOWED_CHAT_ID)

    while True:
        try:
            app = build_app()
            # drop_pending_updates=True: eski update larni tashlab yuboradi
            app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
        except Conflict:
            # 2 ta instans bir payt ishlasa conflict bo'ladi. Bot o‘chib ketmasin.
            log.warning("⚠️ Conflict: boshqa instans polling qilyapti. 15s kutib qayta urinaman...")
            time.sleep(15)
        except (TimedOut, NetworkError) as e:
            log.warning("⚠️ Network/Timeout: %s. 10s kutib qayta urinaman...", e)
            time.sleep(10)
        except Exception as e:
            log.exception("❌ Kutilmagan xato: %s. 10s kutib qayta urinaman...", e)
            time.sleep(10)

if __name__ == "__main__":
    main()
