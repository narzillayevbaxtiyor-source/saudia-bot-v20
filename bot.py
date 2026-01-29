import os
import re
import logging
from typing import Dict, List

from telegram import Update
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

# ================== TOPICS + KEYWORDS ==================
# Siz bergan IDlar:
# Uy-joy & Ijara = 5
# Ish & Daromad = 6
# Transport & Taksi = 7
# Hujjatlar & Visa = 8
# Bozor & Narxlar = 9
# Ziyorat & Umra = 10
# Salomatlik = 11
# Umumiy savollar = 12

TOPICS: Dict[str, Dict[str, List[str] or int]] = {
    "Uy-joy & Ijara": {
        "id": 5,
        "keywords": [
            # lotin
            "uy", "uy-joy", "ijara", "kvartira", "xona", "xonadon", "yotoqxona", "hostel",
            "arenda", "ijaraga", "ijara uy", "uy topish", "kira", "depozit", "zalog",
            "renta", "komunal", "kommunal", "internet", "wifi", "mebel", "mebellik",
            "shartnoma", "dogovor",
            # krill
            "уй", "уй-жой", "ижара", "квартира", "хона", "хонaдон", "ётоқхона",
            "аренда", "уй топиш", "кира", "депозит", "залог", "шартнома", "договор",
            # ruscha
            "квартира", "аренда", "снять", "сдаю", "комната", "общежитие", "залог",
        ],
    },
    "Ish & Daromad": {
        "id": 6,
        "keywords": [
            # lotin
            "ish", "ish bor", "ish topish", "vakansiya", "rezume", "cv", "ish haqqi",
            "oylik", "maosh", "daromad", "kuryer", "dostavka", "delivery", "part time",
            "to'liq stavka", "ishchi", "usta", "shogird",
            # krill
            "иш", "иш бор", "иш топиш", "вакансия", "резюме", "ойлик", "маош",
            "даромад", "курьер", "доставка", "ишчи", "уста", "шогирд",
            # ruscha
            "работа", "вакансия", "подработка", "зарплата", "курьер", "доставка",
        ],
    },
    "Transport & Taksi": {
        "id": 7,
        "keywords": [
            # lotin
            "taksi", "uber", "careem", "bolt", "transport", "avtobus", "bus", "metro",
            "yo'l", "marshrut", "velosiped", "skuter", "mashina", "avto", "benzin",
            "parkovka", "jarima", "gps", "lokatsiya",
            # krill
            "такси", "убер", "карим", "транспорт", "автобус", "метро", "йўл",
            "маршрут", "велосипед", "скутер", "машина", "бензин", "парковка", "жарима",
            # ruscha
            "такси", "uber", "careem", "автобус", "метро", "штраф", "парковка",
        ],
    },
    "Hujjatlar & Visa": {
        "id": 8,
        "keywords": [
            # lotin
            "viza", "visa", "iqoma", "iqama", "pasport", "passport", "hujjat", "dokument",
            "tasrix", "tasrih", "tasreh", "tasreeh", "tashrix", "muhr", "registratsiya",
            "sug'urta", "insurance", "muddat", "muddati", "kafolat", "kafil",
            "jarayon", "anketa", "biometrik",
            # krill
            "виза", "виса", "иқома", "паспорт", "ҳужжат", "документ",
            "тасрих", "тасрих", "муҳр", "регистрация", "суғурта", "муддат", "кафил",
            # ruscha
            "виза", "паспорт", "идентификация", "икама", "документы", "страховка",
        ],
    },
    "Bozor & Narxlar": {
        "id": 9,
        "keywords": [
            # lotin
            "bozor", "narx", "qimmat", "arzon", "chegirma", "skidka", "do'kon", "market",
            "magazin", "sotib olish", "sotiladi", "olaman", "kurs", "valyuta", "sar",
            # krill
            "бозор", "нарх", "қиммат", "арзон", "чегирма", "сккидка", "дўкон", "маркет",
            "магазин", "сотиб олиш", "сотилади", "курс",
            # ruscha
            "цена", "рынок", "дешево", "дорого", "скидка", "магазин", "купить",
        ],
    },
    "Ziyorat & Umra": {
        "id": 10,
        "keywords": [
            # lotin
            "ziyorat", "umra", "haj", "makka", "makka", "madina", "masjid", "rawza",
            "ravza", "nusuk", "haram", "tawaf", "tavof", "sa'y", "sa'y", "ihram",
            "ziyorat joylari", "manosik",
            # krill
            "зиёрат", "умра", "ҳаҗ", "макка", "мадина", "масжид", "равза", "ҳарам",
            "тавoф", "саъй", "иҳром",
            # ruscha
            "умра", "хадж", "мекка", "медина", "таваф", "саи", "ихрам",
        ],
    },
    "Salomatlik": {
        "id": 11,
        "keywords": [
            # lotin
            "kasal", "og'riq", "dori", "doktor", "shifokor", "kasalxona", "apteka",
            "allergiya", "isitma", "yo'tal", "bosim", "tomoq", "tish", "tez yordam",
            # krill
            "касал", "оғриқ", "дори", "доктор", "шифокор", "касалхона", "аптека",
            "аллергия", "иситма", "йўтал", "босим", "томоқ", "тиш",
            # ruscha
            "врач", "больница", "аптека", "лекарство", "аллергия", "температура",
        ],
    },
    "Umumiy savollar": {
        "id": 12,
        "keywords": [
            # lotin
            "savol", "qanday", "qayerda", "qachon", "yordam", "maslahat",
            # krill
            "савол", "қандай", "қаерда", "қачон", "ёрдам", "маслаҳат",
            # ruscha
            "вопрос", "как", "где", "когда", "помогите",
        ],
    },
}

# Oldindan regex tayyorlab qo'yamiz (tezroq ishlashi uchun)
def _compile_keywords(topic_keywords: List[str]):
    # \b bilan ishlasa krill/uzbek apostrofda qiyin bo'lishi mumkin, shuning uchun "contains" + normalizatsiya
    # Bu yerda regex ishlatmaymiz — pastda oddiy "in" ishlatamiz.
    return topic_keywords

for _t in TOPICS.values():
    _t["keywords"] = _compile_keywords(_t["keywords"])

# ================== HELPERS ==================
def normalize_text(s: str) -> str:
    s = s.lower().strip()
    s = s.replace("’", "'").replace("`", "'")
    s = re.sub(r"\s+", " ", s)
    return s

def find_topic_id(text: str) -> int:
    t = normalize_text(text)
    for name, data in TOPICS.items():
        for kw in data["keywords"]:
            if kw and kw in t:
                return int(data["id"])
    return int(TOPICS["Umumiy savollar"]["id"])

def allowed_chat(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.id == ALLOWED_CHAT_ID)

# ================== HANDLERS ==================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # faqat shu guruhda ishlaydi
    if not allowed_chat(update):
        return
    await update.message.reply_text(
        "👋 Assalomu alaykum!\n\nSavolingizni yozing — bot uni avtomatik ravishda to‘g‘ri bo‘limga (topic) joylaydi 🤖"
    )

async def topics_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed_chat(update):
        return
    lines = ["📌 Topiclar ro‘yxati (ID):"]
    for name, data in TOPICS.items():
        lines.append(f"• {name} = {data['id']}")
    await update.message.reply_text("\n".join(lines))

async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if not allowed_chat(update):
        return

    # buyruqlarni bu handlerga kiritmaymiz (filters.COMMAND bilan to'siladi)
    text = update.message.text
    topic_id = find_topic_id(text)

    # Agar user topic ichida yozgan bo'lsa ham, biz uni kerakli topicga ko'chiramiz:
    try:
        await context.bot.copy_message(
            chat_id=update.effective_chat.id,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
            message_thread_id=topic_id,
        )
        # ixtiyoriy: userga qisqa tasdiq (spam bo'lmasin desangiz kommentni o'chiring)
        # await update.message.reply_text(f"✅ Topicga joylandi: {topic_id}")
    except Exception as e:
        log.exception("copy_message error: %s", e)

# ================== MAIN ==================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler(["start"], start_cmd))
    app.add_handler(CommandHandler(["topics"], topics_cmd))

    # Faqat oddiy text xabarlar
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

    log.info("✅ Saudiya Smart Topic Bot ishga tushdi (faqat bitta guruh uchun).")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
