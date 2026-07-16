"""
תוכן תורני לערוץ ייעודי: זמני הלכה + דף יומי (מ-haredi_updates.py),
משנה יומית / רמב"ם היומי / תנ"ך יומי (מ-Sefaria - ציטוט מקור בלבד, לא טקסט מלא),
ופתגמים מתחלפים מפרקי אבות + פסוק היום (טקסט עתיק, נחלת הכלל, קצר).
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from haredi_updates import get_zmanim_text, get_daf_yomi_text

log = logging.getLogger("bot1")
IL_TZ = ZoneInfo("Asia/Jerusalem")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; bothamal-bot/1.0)"}

# מבחר מפרקי אבות - טקסט עתיק ונחלת הכלל, כל פריט קצר ומצוטט עם מקור.
PIRKEI_AVOT_QUOTES = [
    ("איזהו עשיר? השמח בחלקו", "פרקי אבות ד, א"),
    ("הוי דן את כל האדם לכף זכות", "פרקי אבות א, ו"),
    ("איזהו חכם? הלומד מכל אדם", "פרקי אבות ד, א"),
    ("בְּמָקוֹם שֶׁאֵין אֲנָשִׁים הִשְׁתַּדֵּל לִהְיוֹת אִישׁ", "פרקי אבות ב, ה"),
    ("אל תסתכל בקנקן אלא במה שיש בו", "פרקי אבות ד, כ"),
    ("עשה תורתך קבע", "פרקי אבות א, טו"),
    ("הוי מתלמידיו של אהרן... אוהב שלום ורודף שלום", "פרקי אבות א, יב"),
    ("לא עליך המלאכה לגמור, ולא אתה בן חורין להיבטל ממנה", "פרקי אבות ב, טז"),
    ("איזהו גיבור? הכובש את יצרו", "פרקי אבות ד, א"),
    ("יפה שעה אחת בתשובה ומעשים טובים בעולם הזה", "פרקי אבות ד, יז"),
    ("הוי זהיר בתלמוד תורה ודע מה שתשיב לאפיקורוס", "פרקי אבות ב, יד"),
    ("כל ישראל יש להם חלק לעולם הבא", "משנה סנהדרין פרק י, משנה א"),
    ("הוי מקדים בשלום כל אדם", "פרקי אבות ד, טו"),
    ("עשה לך רב, וקנה לך חבר", "פרקי אבות א, ו"),
    ("אם אין אני לי מי לי, וכשאני לעצמי מה אני", "פרקי אבות א, יד"),
    ("מרבה עצה מרבה תבונה", "פרקי אבות ב, ז"),
    ("הוי זנב לאריות ואל תהי ראש לשועלים", "פרקי אבות ד, טו"),
    ("שתוק וקבל שכר", "פרקי אבות ד, כג"),
    ("הסתכל בשלושה דברים ואי אתה בא לידי עבירה: דע מה למעלה ממך", "פרקי אבות ב, א"),
    ("על שלושה דברים העולם עומד: על התורה ועל העבודה ועל גמילות חסדים", "פרקי אבות א, ב"),
    ("במקום שאין איש, השתדל להיות איש", "פרקי אבות ב, ה"),
    ("אין לך אדם שאין לו שעה, ואין לך דבר שאין לו מקום", "פרקי אבות ד, ג"),
    ("כל שרוח הבריות נוחה הימנו, רוח המקום נוחה הימנו", "פרקי אבות ג, י"),
    ("הוי גולה למקום תורה", "פרקי אבות ד, יד"),
    ("איזוהי דרך ישרה שידבק בה האדם? עין טובה", "פרקי אבות ב, ט"),
    ("שלושה כתרים הם: כתר תורה, כתר כהונה, וכתר מלכות - וכתר שם טוב עולה על גביהן", "פרקי אבות ד, יג"),
    ("לפום צערא אגרא", "פרקי אבות ה, כג"),
]

# פסוקים קצרים מהתנ"ך - נחלת הכלל, מתחלף לפי יום בחודש
VERSE_OF_DAY = [
    ("ה' עוז לעמו יתן, ה' יברך את עמו בשלום", "תהלים כ״ט, יא"),
    ("טוב ה' לכל, ורחמיו על כל מעשיו", "תהלים קמ״ה, ט"),
    ("דע לפני מי אתה עומד", "מסורת חז\"ל - ברכות כח ע\"ב"),
    ("לא בחיל ולא בכח כי אם ברוחי, אמר ה' צבאות", "זכריה ד, ו"),
    ("טוב לחסות בה' מבטח באדם", "תהלים קי״ח, ח"),
    ("סור מרע ועשה טוב, בקש שלום ורדפהו", "תהלים ל״ד, טו"),
    ("איזהו מכובד? המכבד את הבריות", "פרקי אבות ד, א"),
    ("ואהבת לרעך כמוך", "ויקרא י״ט, יח"),
    ("בכל דרכיך דעהו והוא יישר אורחותיך", "משלי ג, ו"),
    ("שיוויתי ה' לנגדי תמיד", "תהלים ט״ז, ח"),
    ("מה טובו אהליך יעקב, משכנותיך ישראל", "במדבר כ״ד, ה"),
    ("טוב אחרית דבר מראשיתו", "קהלת ז, ח"),
    ("הוי עז כנמר וקל כנשר ורץ כצבי וגיבור כארי לעשות רצון אביך שבשמים", "פרקי אבות ה, כ"),
    ("אשרי אדם עוז לו בך", "תהלים פ״ד, ו"),
    ("פותח את ידך ומשביע לכל חי רצון", "תהלים קמ״ה, טז"),
]


def get_dvar_torah_text() -> str:
    try:
        now = datetime.now(IL_TZ)
        slot = now.hour * 2 + (1 if now.minute >= 30 else 0)
        quote, source = PIRKEI_AVOT_QUOTES[slot % len(PIRKEI_AVOT_QUOTES)]
        return f'📖 **פתגם מפרקי אבות**\n"{quote}"\n_{source}_'
    except Exception as e:
        log.error(f"torah_updates: כשל בבניית פתגם מפרקי אבות: {e}")
        return ""


def get_verse_of_day_text() -> str:
    try:
        day_index = datetime.now(IL_TZ).day
        verse, source = VERSE_OF_DAY[day_index % len(VERSE_OF_DAY)]
        return f'✨ **פסוק היום**\n"{verse}"\n_{source}_'
    except Exception as e:
        log.error(f"torah_updates: כשל בבניית פסוק היום: {e}")
        return ""


def _sefaria_calendar_item(title_en: str):
    """שולף פריט בודד מלוח הלימוד היומי של Sefaria (ציטוט מקור בלבד, לא הטקסט המלא)."""
    try:
        url = "https://www.sefaria.org/api/calendars"
        params = {"diaspora": 0}  # לוח ישראל
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        items = r.json().get("calendar_items", [])
        for it in items:
            if it.get("title", {}).get("en") == title_en:
                return it.get("displayValue", {}).get("he") or it.get("displayValue", {}).get("en")
        return None
    except Exception as e:
        log.error(f"torah_updates: כשל בשליפת {title_en} מ-Sefaria: {e}")
        return None


def get_mishna_yomit_text() -> str:
    val = _sefaria_calendar_item("Daily Mishnah")
    return f"📘 **משנה יומית:** {val}" if val else ""


def get_rambam_yomi_text() -> str:
    val = _sefaria_calendar_item("Daily Rambam") or _sefaria_calendar_item("Daily Rambam (3 Chapters)")
    return f"📗 **רמב\"ם היומי:** {val}" if val else ""


def get_tanakh_yomi_text() -> str:
    val = _sefaria_calendar_item("929")
    return f"📙 **תנ\"ך יומי (929):** {val}" if val else ""


def build_torah_message() -> str:
    """מרכיב הודעה תורנית מכמה מקורות. אם מקור נכשל - פשוט לא מופיע, שאר המקורות עדיין נשלחים."""
    sections = [
        get_dvar_torah_text(),
        get_verse_of_day_text(),
        get_zmanim_text(),
        get_daf_yomi_text(),
        get_mishna_yomit_text(),
        get_rambam_yomi_text(),
        get_tanakh_yomi_text(),
    ]
    sections = [s for s in sections if s]
    if not sections:
        return ""
    divider = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
    header = f"📖✨ **פינת תורה** ✨\n{divider}"
    return f"{header}\n\n" + f"\n\n{divider}\n\n".join(sections)
