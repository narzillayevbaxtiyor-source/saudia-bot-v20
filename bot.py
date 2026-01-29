import os
import re
import time
import logging
from typing import Dict, List

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
TOPICS: Dict[str, Dict[str, object]] = {
    "Uy-joy & Ijara": {
        "id": 5,
        "keywords": [
            # lotin
            "uy", "uy-joy", "ijara", "ijaraga", "ijara uy", "uy topish", "uy qidiryapman",
            "kvartira", "kvartiraga", "xona", "xonadon", "yotoqxona", "hostel", "otel",
            "arenda", "arendaga", "kira", "depozit", "zalog", "renta",
            "shartnoma", "dogovor", "kelishuv",
            "kommunal", "komunal", "elektr", "svet", "gaz", "suv", "internet", "wifi",
            "mebel", "mebellik", "konditsioner", "konditsaner", "klimat",
            "ko'chib o'tish", "ko'chish", "manzil", "lokatsiya",
            # krill
            "уй", "уй-жой", "ижара", "ижарага", "ижара уй", "уй топиш", "уй қидиряпман",
            "квартира", "хона", "хонaдон", "ётоқхона", "хостел", "отель",
            "аренда", "кира", "депозит", "залог",
            "шартнома", "договор", "келишув",
            "коммунал", "электр", "свет", "газ", "сув", "интернет", "вайфай",
            # rus
            "квартира", "аренда", "снять", "сдаю", "сдам", "комната", "общежитие",
            "залог", "договор", "коммуналка", "интернет", "wi-fi",
        ],
    },
    "Ish & Daromad": {
        "id": 6,
        "keywords": [
            "ish", "ish bor", "ish topish", "vakansiya", "rezume", "cv",
            "oylik", "maosh", "daromad", "ish haqqi", "stavka", "part time", "full time",
            "kuryer", "dostavka", "delivery", "haydovchi", "operator", "sotuvchi",
            "usta", "shogird", "ishchi",
            # krill
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
            "taksi", "taxi", "uber", "careem", "karim", "bolt",
            "transport", "avtobus", "bus", "metro", "poezd", "train",
            "yo'l", "marshrut", "bekat", "stansiya",
            "velosiped", "skuter", "mashina", "avto", "benzin", "parkovka", "jarima",
            "gps", "lokatsiya", "navigatsiya",
            # krill
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
            "viza", "visa", "iqoma", "iqama", "pasport", "passport", "hujjat", "dokument",
            "tasrix", "tasrih", "tasreh", "tasreeh", "tashrix", "tashrih",
            "muhr", "registratsiya", "ro'yxat", "registration",
            "sug'urta", "insurance", "muddat", "muddati", "kafolat", "kafil",
            "anketa", "biometrik", "fingerprint",
            "stc", "absher", "abshar",
            # krill
            "виза", "виса", "иқома", "паспорт", "ҳужжат", "документ",
            "тасрих", "ташрих", "муҳр", "регистрация", "рўйхат",
            "суғурта", "муддат", "кафил", "анкета", "биометрик",
            # rus
            "виза", "паспорт", "икама", "документы", "страховка", "регистрация",
            "разрешение", "tasreeh",
        ],
    },
    "Bozor & Narxlar": {
        "id": 9,
        "keywords": [
            "bozor", "narx", "qimmat", "arzon", "chegirma", "skidka",
            "do'kon", "market", "magazin", "sotib olish", "sotiladi", "olaman",
            "kurs", "valyuta", "sar", "riyal", "riyo'l",
            # krill
            "бозор", "нарх", "қиммат", "арзон", "чегирма", "дўкон", "маркет",
            "магазин", "курс", "валюта", "риал",
            # rus
            "цена", "рынок", "дешево", "дорого", "скидка", "магазин", "купить",
        ],
    },
    "Ziyorat & Umra": {
        "id": 10,
        "keywords": [
            "ziyorat", "umra", "haj", "makka", "madina", "masjid", "rawza", "ravza",
            "nusuk", "haram", "tawaf", "tavof", "sa'y", "say", "ihram", "manosik",
            "bilet", "avia bilet", "aviabilet", "reys", "flight", "chipta",
            # krill
            "зиёрат", "умра", "ҳаҗ", "макка", "мадина", "масжид", "равза", "ҳарам",
            "тавoф", "саъй", "иҳром",
            "билет", "авиабилет", "рейс", "чипта",
            # rus
            "умра", "хадж", "мекка", "медина", "таваф", "саи", "ихрам",
            "билет", "авиабилет", "рейс", "самолет",
        ],
    },
    "Salomatlik": {
        "id": 11,
        "keywords": [
            "kasal", "og'riq", "dori", "doktor", "shifokor", "kasalxona", "apteka",
            "allergiya", "isitma", "yo'tal", "bosim", "tomoq", "tish", "tez yordam",
            # krill
            "касал", "оғриқ", "дори", "доктор", "шифокор", "касалхона", "аптека",
            "аллергия", "иситма", "йўтал", "босим", "томоқ", "тиш",
            # rus
            "врач", "больница", "аптека", "лекарство", "аллергия", "температура",
        ],
    },
    "Umumiy savollar": {
        "id": 1,
        "keywords": [
            "savol", "qanday", "qayerda", "qachon", "yordam", "maslahat", "bilasizmi",
            "савол", "қандай", "қаерда", "қачон", "ёрдам", "маслаҳат",
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

    for data in COMPILED.values():
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

    if getattr(chat, "username", None):
        return f"https://t.me/{chat.username}/{topic_id}"

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
    target_topic_id = find_topic_id(text)
    current_tid = getattr(msg, "message_thread_id", None)

    # ✅ Jimlik: agar user to‘g‘ri bo‘limda yozgan bo‘lsa — hech narsa qilmaymiz
    if current_tid == target_topic_id:
        return

    # 1) Xabarni to‘g‘ri topicga ko‘chiramiz
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

    # 2) Faqat noto‘g‘ri bo‘limda yozganda reply qilamiz (mobil ko‘rinish + oxiri 👇)
    try:
        topic_name = ID_TO_NAME.get(target_topic_id, "kerakli bo‘lim")
        link = build_topic_link(update, target_topic_id)

        reply_text = (
            "Iltimos, bu masalani 👇\n\n"
            f"**{topic_name}**\n\n"
            "bo‘limiga yozing:\n\n"
            f"{link} 👇"
        )

        await msg.reply_text(reply_text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        log.exception("reply with link error")

# ================== MAIN (STABLE) ==================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler(["start"], start_cmd))
    app.add_handler(CommandHandler(["topics"], topics_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

    log.info("✅ Saudiya Smart Topic Bot ishga tushdi (faqat bitta guruh uchun). ALLOWED_CHAT_ID=%s", ALLOWED_CHAT_ID)

    # ⚠️ Event loop muammosiz: while True yo‘q, Updater yo‘q
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
