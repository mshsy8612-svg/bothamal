"""
תוכן תורני לערוץ ייעודי, מאורגן בקטגוריות:
1. זמנים ולוח יהודי (זמני הלכה + כל תוכניות הלימוד היומי)
2. מחשבה ומוסר (פרקי אבות, פסוקים, אמרות חז"ל - טקסט עתיק/נחלת הכלל)

מקורות: Hebcal.com + Sefaria.org (שני APIs חינמיים, ציטוט מקור בלבד - לא טקסט מלא).
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from haredi_updates import get_zmanim_text, get_daf_yomi_value, get_next_holiday_text
from hourly_updates import get_weather_text

log = logging.getLogger("bot1")
IL_TZ = ZoneInfo("Asia/Jerusalem")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; bothamal-bot/1.0)"}

# ══════════════════════════════════════════════════════════════
# קטגוריה: מחשבה ומוסר - טקסטים עתיקים, נחלת הכלל, כל פריט קצר ומצוטט
# ══════════════════════════════════════════════════════════════
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
    ("על שלושה דברים העולם עומד: על התורה ועל העבודה ועל גמילות חסדים", "פרקי אבות א, ב"),
    ("אין לך אדם שאין לו שעה, ואין לך דבר שאין לו מקום", "פרקי אבות ד, ג"),
    ("כל שרוח הבריות נוחה הימנו, רוח המקום נוחה הימנו", "פרקי אבות ג, י"),
    ("הוי גולה למקום תורה", "פרקי אבות ד, יד"),
    ("איזוהי דרך ישרה שידבק בה האדם? עין טובה", "פרקי אבות ב, ט"),
    ("שלושה כתרים הם: כתר תורה, כתר כהונה, וכתר מלכות - וכתר שם טוב עולה על גביהן", "פרקי אבות ד, יג"),
    ("לפום צערא אגרא", "פרקי אבות ה, כג"),
]

VERSE_OF_DAY = [
    ("ה' עוז לעמו יתן, ה' יברך את עמו בשלום", "תהלים כ״ט, יא"),
    ("טוב ה' לכל, ורחמיו על כל מעשיו", "תהלים קמ״ה, ט"),
    ("דע לפני מי אתה עומד", "מסורת חז\"ל - ברכות כח ע\"ב"),
    ("לא בחיל ולא בכח כי אם ברוחי, אמר ה' צבאות", "זכריה ד, ו"),
    ("טוב לחסות בה' מבטח באדם", "תהלים קי״ח, ח"),
    ("סור מרע ועשה טוב, בקש שלום ורדפהו", "תהלים ל״ד, טו"),
    ("ואהבת לרעך כמוך", "ויקרא י״ט, יח"),
    ("בכל דרכיך דעהו והוא יישר אורחותיך", "משלי ג, ו"),
    ("שיוויתי ה' לנגדי תמיד", "תהלים ט״ז, ח"),
    ("מה טובו אהליך יעקב, משכנותיך ישראל", "במדבר כ״ד, ה"),
    ("טוב אחרית דבר מראשיתו", "קהלת ז, ח"),
    ("הוי עז כנמר וקל כנשר ורץ כצבי וגיבור כארי לעשות רצון אביך שבשמים", "פרקי אבות ה, כ"),
    ("אשרי אדם עוז לו בך", "תהלים פ״ד, ו"),
    ("פותח את ידך ומשביע לכל חי רצון", "תהלים קמ״ה, טז"),
    ("עולם חסד ייבנה", "תהלים פ״ט, ג"),
]

# אמרות חז"ל מהתלמוד והמדרש - נחלת הכלל, קצרות ומצוטטות
TALMUD_SAYINGS = [
    ("כל המקיים נפש אחת מישראל כאילו קיים עולם מלא", "משנה סנהדרין ד, ה"),
    ("איזהו גיבור שבגיבורים? הכובש את יצרו", "אבות דרבי נתן, פרק כג"),
    ("מרבה צדקה מרבה שלום", "פרקי אבות ב, ז"),
    ("חייב אדם לומר: מתי יגיעו מעשי למעשה אבותי", "תנא דבי אליהו רבה"),
    ("כל השונה הלכות בכל יום מובטח לו שהוא בן העולם הבא", "מגילה כח ע\"ב"),
    ("גדולה מלאכה שמכבדת את בעליה", "נדרים מט ע\"ב"),
    ("הוי מן הנעלבים ואינם עולבים", "גיטין לו ע\"ב"),
    ("איזהו מכובד? המכבד את הבריות", "פרקי אבות ד, א"),
    ("כל המצער חברו אפילו בדברים חייב", "בבא מציעא נח ע\"ב"),
    ("תלמידי חכמים מרבים שלום בעולם", "ברכות סד ע\"א"),
    ("אין אדם לומד תורה אלא במקום שליבו חפץ", "עבודה זרה יט ע\"א"),
    ("כל המלמד את בן חברו תורה - מעלה עליו הכתוב כאילו ילדו", "סנהדרין יט ע\"ב"),
]


def get_dvar_torah_text() -> str:
    try:
        now = datetime.now(IL_TZ)
        slot = now.hour
        quote, source = PIRKEI_AVOT_QUOTES[slot % len(PIRKEI_AVOT_QUOTES)]
        return f'"{quote}"\n_{source}_'
    except Exception as e:
        log.error(f"torah_updates: כשל בבניית פתגם מפרקי אבות: {e}")
        return ""


def get_verse_of_day_text() -> str:
    try:
        day_index = datetime.now(IL_TZ).day
        verse, source = VERSE_OF_DAY[day_index % len(VERSE_OF_DAY)]
        return f'"{verse}"\n_{source}_'
    except Exception as e:
        log.error(f"torah_updates: כשל בבניית פסוק היום: {e}")
        return ""


def get_talmud_saying_text() -> str:
    try:
        now = datetime.now(IL_TZ)
        idx = now.hour  # מתחלף כל שעה (שונה מקצב פרקי אבות, כדי לא לחזור על אותו שילוב)
        saying, source = TALMUD_SAYINGS[idx % len(TALMUD_SAYINGS)]
        return f'"{saying}"\n_{source}_'
    except Exception as e:
        log.error(f"torah_updates: כשל בבניית אמרת חז\"ל: {e}")
        return ""


# ══════════════════════════════════════════════════════════════
# קטגוריה: לוח לימוד יומי - מ-Sefaria (ציטוט מקור בלבד, לא טקסט מלא)
# שליפה אחת בלבד לכל ה-API, כדי לא לבזבז קריאות רשת מיותרות
# ══════════════════════════════════════════════════════════════
SEFARIA_DAILY_ITEMS = [
    ("Daily Mishnah", "📘 משנה יומית"),
    ("Daily Rambam", "📗 רמב\"ם היומי"),
    ("Daily Rambam (3 Chapters)", "📗 רמב\"ם היומי (3 פרקים)"),
    ("929", "📙 תנ\"ך יומי (929)"),
    ("Halakhah Yomit", "⚖️ הלכה יומית"),
    ("Tanya Yomi", "🔥 תניא יומי"),
    ("Arukh HaShulchan Yomi", "📜 ערוך השולחן היומי"),
    ("Chok LeYisrael", "📕 חוק לישראל"),
    ("Yerushalmi Yomi", "📔 ירושלמי יומי"),
]


def _fetch_sefaria_calendar():
    try:
        url = "https://www.sefaria.org/api/calendars"
        params = {"diaspora": 0}  # לוח ישראל
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json().get("calendar_items", [])
    except Exception as e:
        log.error(f"torah_updates: כשל בשליפת לוח הלימוד מ-Sefaria: {e}")
        return []


def get_sefaria_learning_lines() -> list:
    """מחזיר רשימת שורות מוכנות (למניעת כפילות: אם גם 'Daily Rambam' וגם הגרסה עם 3 פרקים
    זמינות, מוצגת רק הראשונה שנמצאה)."""
    items = _fetch_sefaria_calendar()
    if not items:
        return []
    by_title = {it.get("title", {}).get("en"): it for it in items}
    lines = []
    used_rambam = False
    for title_en, label in SEFARIA_DAILY_ITEMS:
        if "Rambam" in title_en:
            if used_rambam:
                continue
        it = by_title.get(title_en)
        if not it:
            continue
        val = it.get("displayValue", {}).get("he") or it.get("displayValue", {}).get("en")
        if not val:
            continue
        lines.append(f"• {label}: {val}")
        if "Rambam" in title_en:
            used_rambam = True
    return lines


def build_torah_message() -> str:
    """מרכיב הודעה תורנית מקוטלגת. כל מקור שנכשל פשוט לא מופיע - שאר המקורות עדיין נשלחים."""
    divider = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
    blocks = []

    # קטגוריה 0: ספירה לחג הבא - בהתחלה, כדי שיהיה בולט מיד
    holiday = get_next_holiday_text()
    if holiday:
        blocks.append(holiday)

    # קטגוריה 1: זמנים הלכתיים
    zmanim = get_zmanim_text()
    if zmanim:
        blocks.append(zmanim)

    # קטגוריה 1.5: מזג אוויר
    weather = get_weather_text()
    if weather:
        blocks.append(weather)

    # קטגוריה 2: לוח לימוד יומי (דף יומי + כל מה שיש מ-Sefaria)
    daf = get_daf_yomi_value()
    sefaria_lines = get_sefaria_learning_lines()
    learning_lines = ([f"📖 דף יומי: {daf}"] if daf else []) + sefaria_lines
    if learning_lines:
        blocks.append("📚 **לוח לימוד יומי**\n" + "\n".join(learning_lines))

    # קטגוריה 3: מחשבה ומוסר
    thoughts = []
    dvar = get_dvar_torah_text()
    if dvar:
        thoughts.append(f"💭 **פתגם מפרקי אבות**\n{dvar}")
    verse = get_verse_of_day_text()
    if verse:
        thoughts.append(f"✨ **פסוק היום**\n{verse}")
    talmud = get_talmud_saying_text()
    if talmud:
        thoughts.append(f"📜 **אמרת חז\"ל**\n{talmud}")
    blocks.extend(thoughts)

    if not blocks:
        return ""
    header = f"📖✨ **פינת תורה** ✨\n{divider}"
    return f"{header}\n\n" + f"\n\n{divider}\n\n".join(blocks)
