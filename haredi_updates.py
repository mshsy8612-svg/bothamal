"""
עדכון יומי (לא שעתי!) עם תוכן רלוונטי לציבור החרדי:
זמנים הלכתיים, דף יומי, פרשת השבוע, ספירת העומר / ראש חודש, יארצייט, זמני צום, מולד, הדלקת נרות.
מקור: Hebcal.com (API חינמי, ללא מפתח). ראו https://www.hebcal.com/home/developer-apis
"""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from cache_utils import cached_get_json

log = logging.getLogger("bot1")
IL_TZ = ZoneInfo("Asia/Jerusalem")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; bothamal-bot/1.0)"}

# ⚠️ הערה חשובה על מקור הזמנים: כל הזמנים ההלכתיים כאן מחושבים ע"י Hebcal.com.
# עמודות "קש-גר״א" ו"קש-מג״א" מציינות אילו שיטת חישוב (הגר"א מול מגן אברהם) לסוף זמן ק"ש.
# "צאת הכוכבים" מחושב לפי שקיעת השמש 8.5 מעלות מתחת לאופק (הגדרת ברירת המחדל של Hebcal).
# יש נוהגים/פוסקים שונים בקהילות שונות - מומלץ לוודא מול פוסק/רב מקומי, בפרט לפני שימוש הלכה למעשה.
ZMANIM_SOURCE_NOTE = (
    '_מקור: Hebcal.com · "קש-גר״א"/"קש-מג״א" = שיטות חישוב שונות לסוף זמן ק"ש · '
    "צאת הכוכבים לפי 8.5° מתחת לאופק. מומלץ לוודא מול פוסק מקומי._"
)


def _today_str() -> str:
    return datetime.now(IL_TZ).strftime("%Y-%m-%d")


def _fmt_time(iso_str: str) -> str:
    """הופך '2026-07-14T05:49:00+03:00' ל-'05:49'"""
    try:
        return datetime.fromisoformat(iso_str).strftime("%H:%M")
    except Exception:
        return "?"


def _get_today_dates_str() -> str:
    """מחזיר מחרוזת עם התאריך העברי והלועזי של היום, למשל 'יום ראשון, י״ט תמוז תשפ״ו · 19.07.2026'"""
    try:
        d = _today_str()
        civil = datetime.now(IL_TZ).strftime("%d.%m.%Y")
        url = f"https://www.hebcal.com/converter?cfg=json&date={d}&g2h=1"
        data = cached_get_json(url, ttl=21600, headers=HEADERS)
        hebrew_date = data.get("hebrew", "")
        weekday = datetime.now(IL_TZ).strftime("%A")
        weekday_he = {
            "Monday": "יום שני", "Tuesday": "יום שלישי", "Wednesday": "יום רביעי",
            "Thursday": "יום חמישי", "Friday": "יום שישי", "Saturday": "שבת", "Sunday": "יום ראשון",
        }.get(weekday, weekday)
        parts = [p for p in [weekday_he, hebrew_date] if p]
        return " · ".join(parts + [civil]) if parts else civil
    except Exception as e:
        log.error(f"haredi_updates: כשל בשליפת תאריך עברי: {e}")
        return datetime.now(IL_TZ).strftime("%d.%m.%Y")


from shabbat import CITIES as _SHABBAT_CITIES

# ערים לזמנים הלכתיים - נשען על אותה רשימת ערים כמו shabbat.py (lat/lon, לא geonameid -
# גילינו שב-shabbat.py יש geonameid כפול בטעות בין אלעד לבאר שבע, אז עדיף קואורדינטות מדויקות),
# ובנוסף טבריה שלא קיימת שם. מודיעין עילית ראשונה (מקבלת את הפירוט המלא).
_PRIMARY_CITY_NAME = "מודיעין עילית"
_ordered = sorted(_SHABBAT_CITIES, key=lambda c: 0 if c["name"] == _PRIMARY_CITY_NAME else 1)
ZMANIM_CITIES = [{"name": c["name"], "lat": c["lat"], "lon": c["lon"]} for c in _ordered]
ZMANIM_CITIES.append({"name": "טבריה", "lat": 32.7922, "lon": 35.5312})


def _get_zmanim_raw(lat: float, lon: float, date_str: str = None):
    """שולף את מילון הזמנים הגולמי (times) מ-Hebcal לפי קואורדינטות. date_str אופציונלי (ברירת מחדל: היום)."""
    d = date_str or _today_str()
    url = (
        "https://www.hebcal.com/zmanim?cfg=json"
        f"&latitude={lat}&longitude={lon}&tzid=Asia/Jerusalem&date={d}"
    )
    data = cached_get_json(url, ttl=3600, headers=HEADERS)
    return data["times"]


# עמודות הזמנים בטבלה: (כותרת קצרה, מפתחות מ-Hebcal לפי סדר עדיפות, שם מלא ללג'נדה)
ZMAN_COLUMNS = [
    ("עלות", ("alotHaShachar",), "עלות השחר"),
    ("נץ", ("sunrise",), "נץ החמה"),
    ("קש-גר״א", ("sofZmanShma",), 'סוף זמן ק"ש (גר"א)'),
    ("קש-מג״א", ("sofZmanShmaMGA",), 'סוף זמן ק"ש (מג"א)'),
    ("תפילה", ("sofZmanTfilla",), "סוף זמן תפילה"),
    ("חצות", ("chatzot",), "חצות היום"),
    ("מנח״ג", ("minchaGedola",), "מנחה גדולה"),
    ("פלג", ("plagHaMincha",), "פלג המנחה"),
    ("שקיעה", ("sunset",), "שקיעה"),
    ("צאת", ("tzeit85deg", "tzeit72min", "tzeit50min", "tzeit42min"), "צאת הכוכבים"),
]


# ══════════════════════════════════════════════════
# זמנים הלכתיים - טבלה אחת מאוחדת לכל הערים (מודיעין עילית ראשונה)
# ══════════════════════════════════════════════════
def get_zmanim_text() -> str:
    if not ZMANIM_CITIES:
        return ""
    lines = []
    date_str = _get_today_dates_str()

    table_rows = []
    for city in ZMANIM_CITIES:
        try:
            t = _get_zmanim_raw(city["lat"], city["lon"])

            def g(*keys):
                for k in keys:
                    if k in t:
                        return _fmt_time(t[k])
                return "--"

            values = [g(*keys) for _, keys, _ in ZMAN_COLUMNS]
            table_rows.append((city["name"], values))
        except Exception as e:
            log.error(f"haredi_updates: כשל בשליפת זמנים ל-{city['name']}: {e}")

    if table_rows:
        headers = ["עיר"] + [h for h, _, _ in ZMAN_COLUMNS]
        md_lines = [
            "| " + " | ".join(headers) + " |",
            "|" + "|".join(["---"] * len(headers)) + "|",
        ]
        for name, values in table_rows:
            md_lines.append("| " + " | ".join([name] + values) + " |")

        lines.append("🕍 **זמני היום - כל הערים**")
        lines.append(f"📅 **{date_str}**")
        lines.append("")
        lines.append("\n".join(md_lines))
        lines.append("")
        lines.append(ZMANIM_SOURCE_NOTE)

    return "\n".join(lines)


# ══════════════════════════════════════════════════
# הדלקת נרות (רק בימי שישי) - מבוסס על shabbat.py הקיים
# ══════════════════════════════════════════════════
def get_candle_lighting_text() -> str:
    if datetime.now(IL_TZ).weekday() != 4:  # 4 = יום שישי
        return ""
    try:
        from shabbat import ShabbatManager
        sb = ShabbatManager()
        lines = ["🕯️ **הדלקת נרות (היום, יום שישי)**"]
        ok = False
        for city in _SHABBAT_CITIES:
            try:
                t = sb.get_times(city, city["standard"])
                if t["candles"]:
                    lines.append(f"• {city['name']}: {t['candles'].strftime('%H:%M')}")
                    ok = True
            except Exception as e:
                log.error(f"haredi_updates: כשל בהדלקת נרות ל-{city['name']}: {e}")
        return "\n".join(lines) if ok else ""
    except Exception as e:
        log.error(f"haredi_updates: כשל כללי בהדלקת נרות: {e}")
        return ""


# ══════════════════════════════════════════════════
# זמני צום (מוצג רק ביום צום עצמו)
# ══════════════════════════════════════════════════
FAST_DAY_TITLES = {"Tzom Tammuz", "Tisha B'Av", "Tzom Gedaliah", "Asara B'Tevet", "Ta'anit Esther"}


def get_fast_times_text() -> str:
    try:
        today = datetime.now(IL_TZ).date()
        start = today - timedelta(days=1)
        end = today + timedelta(days=1)
        url = (
            "https://www.hebcal.com/hebcal?cfg=json&v=1&maj=on&min=on&i=on"
            f"&start={start.isoformat()}&end={end.isoformat()}"
        )
        data = cached_get_json(url, ttl=21600, headers=HEADERS)
        items = data.get("items", [])
        fast_today = next(
            (it for it in items if it.get("title", "").strip() in FAST_DAY_TITLES
             and it.get("date", "").startswith(today.isoformat())),
            None,
        )
        if not fast_today:
            return ""

        title = fast_today.get("title", "")
        is_tisha_bav = "Tisha" in title
        primary = ZMANIM_CITIES[0]

        if is_tisha_bav:
            prev_day = (today - timedelta(days=1)).isoformat()
            prev_t = _get_zmanim_raw(primary["lat"], primary["lon"], date_str=prev_day)
            start_time = _fmt_time(prev_t.get("sunset", ""))
        else:
            t = _get_zmanim_raw(primary["lat"], primary["lon"])
            start_time = _fmt_time(t.get("alotHaShachar", t.get("sunrise", "")))

        t2 = _get_zmanim_raw(primary["lat"], primary["lon"])
        end_time = _fmt_time(t2.get("tzeit85deg", t2.get("tzeit72min", "")))
        fast_name_he = fast_today.get("hebrew", title)
        return (
            f"🕯️ **{fast_name_he} - זמני הצום ({primary['name']}):**\n"
            f"• תחילת הצום: {start_time}\n"
            f"• סוף הצום: {end_time}\n"
            "_זמן סיום מבוסס על צאת הכוכבים הרגיל - מומלץ לוודא מול פוסק מקומי._"
        )
    except Exception as e:
        log.error(f"haredi_updates: כשל בחישוב זמני צום: {e}")
        return ""


# ══════════════════════════════════════════════════
# דף יומי
# ══════════════════════════════════════════════════
def get_daf_yomi_value() -> str:
    """מחזיר רק את הערך הגולמי (למשל 'חולין דף פ'), בלי עיצוב - לשימוש כשצריך להרכיב טקסט בעצמך."""
    try:
        d = _today_str()
        url = f"https://www.hebcal.com/hebcal?cfg=json&v=1&F=on&start={d}&end={d}"
        data = cached_get_json(url, ttl=21600, headers=HEADERS)
        items = data.get("items", [])
        daf = next((it for it in items if it.get("category") == "dafyomi"), None)
        if not daf:
            return ""
        return daf.get("hebrew", daf.get("title", ""))
    except Exception as e:
        log.error(f"haredi_updates: כשל בשליפת דף יומי: {e}")
        return ""


def get_daf_yomi_text() -> str:
    val = get_daf_yomi_value()
    return f"📖 **דף יומי:** {val}" if val else ""


# ══════════════════════════════════════════════════
# פרשת השבוע + ספירה לימים עד שבת
# ══════════════════════════════════════════════════
def get_parasha_text() -> str:
    try:
        start = datetime.now(IL_TZ).date()
        end = start + timedelta(days=8)  # מבטיח שבת אחת לפחות בטווח
        url = (
            "https://www.hebcal.com/hebcal?cfg=json&v=1&s=on&i=on"
            f"&start={start.isoformat()}&end={end.isoformat()}"
        )
        data = cached_get_json(url, ttl=21600, headers=HEADERS)
        items = data.get("items", [])
        parasha = next((it for it in items if it.get("category") == "parashat"), None)
        if not parasha:
            return ""
        name = parasha.get("hebrew", parasha.get("title", ""))
        parasha_date = datetime.fromisoformat(parasha["date"]).date()
        days_left = (parasha_date - start).days
        when = "השבת הקרובה" if days_left <= 1 else f"בעוד {days_left} ימים"
        return f"📜 **פרשת השבוע:** {name} ({when})"
    except Exception as e:
        log.error(f"haredi_updates: כשל בשליפת פרשת השבוע: {e}")
        return ""


# ══════════════════════════════════════════════════
# ספירת העומר / ראש חודש / מולד (מוצג רק כשרלוונטי)
# ══════════════════════════════════════════════════
def get_omer_or_roshchodesh_text() -> str:
    try:
        d = _today_str()
        url = f"https://www.hebcal.com/hebcal?cfg=json&v=1&o=on&nx=on&start={d}&end={d}"
        data = cached_get_json(url, ttl=21600, headers=HEADERS)
        items = data.get("items", [])
        omer = next((it for it in items if it.get("category") == "omer"), None)
        if omer:
            return f"🔥 **ספירת העומר:** {omer.get('hebrew', omer.get('title', ''))}"
        rc = next((it for it in items if it.get("category") == "roshchodesh"), None)
        if rc:
            return f"🌙 **ראש חודש:** {rc.get('hebrew', rc.get('title', ''))}"
        return ""
    except Exception as e:
        log.error(f"haredi_updates: כשל בשליפת עומר/ראש חודש: {e}")
        return ""


def get_molad_text() -> str:
    """מוצג רק בשבת מברכים (השבת שלפני ראש חודש) - Hebcal מפרסם אז פריט 'מולד' עם הנוסח המלא."""
    try:
        start = datetime.now(IL_TZ).date()
        end = start + timedelta(days=7)
        url = (
            "https://www.hebcal.com/hebcal?cfg=json&v=1&nx=on&mod=on"
            f"&start={start.isoformat()}&end={end.isoformat()}"
        )
        data = cached_get_json(url, ttl=21600, headers=HEADERS)
        items = data.get("items", [])
        molad = next(
            (it for it in items if it.get("category") == "molad" or "Molad" in it.get("title", "")),
            None,
        )
        if not molad:
            return ""
        return f"🌒 **המולד:** {molad.get('hebrew', molad.get('title', ''))}"
    except Exception as e:
        log.error(f"haredi_updates: כשל בשליפת מולד: {e}")
        return ""


# ══════════════════════════════════════════════════
# יארצייט - רשימה ידנית מצומצמת של גדולי ישראל מוכרים
# ⚠️ חשוב: התאריכים כאן הוזנו ידנית ולא אומתו מול מקור הלכתי רשמי.
# מומלץ לבדוק ולעדכן לפני שימוש בפועל!
# מפתח: (חודש עברי, יום עברי) בכתיב Hebcal - Tishrei, Cheshvan, Kislev, Tevet,
# Sh'vat, Adar, Adar I, Adar II, Nisan, Iyyar, Sivan, Tamuz, Av, Elul
# ══════════════════════════════════════════════════
YAHRZEIT_LIST = {
    ("Elul", 24): "רבי ישראל מאיר הכהן - ה'חפץ חיים'",
    ("Kislev", 5): "רבי אברהם ישעיהו קרליץ - ה'חזון איש'",
    ("Cheshvan", 20): "רבי יעקב ישראל קניבסקי - ה'סטייפלר'",
    ("Tamuz", 3): "הרבי מליובאוויטש - רבי מנחם מנדל שניאורסון",
    ("Sh'vat", 27): "הבבא סאלי - רבי ישראל אבוחצירא",
    ("Tishrei", 3): "רבי עובדיה יוסף",
    ("Adar", 5): "רבי אהרן קוטלר",
    ("Sivan", 19): "רבי משה פיינשטיין",
}


def get_yahrzeit_text() -> str:
    try:
        d = _today_str()
        url = f"https://www.hebcal.com/converter?cfg=json&date={d}&g2h=1"
        data = cached_get_json(url, ttl=21600, headers=HEADERS)
        key = (data["hm"], data["hd"])
        name = YAHRZEIT_LIST.get(key)
        if not name:
            return ""
        return f"🕯️ **יארצייט היום:** {name}"
    except Exception as e:
        log.error(f"haredi_updates: כשל בבדיקת יארצייט: {e}")
        return ""


def get_next_holiday_text() -> str:
    """מחשב כמה ימים נשארו לחג/מועד הקרוב ביותר (מה-60 יום הקרובים)."""
    try:
        start = datetime.now(IL_TZ).date()
        end = start + timedelta(days=60)
        url = (
            "https://www.hebcal.com/hebcal?cfg=json&v=1&maj=on&min=on&i=on"
            f"&start={start.isoformat()}&end={end.isoformat()}"
        )
        data = cached_get_json(url, ttl=21600, headers=HEADERS)
        items = data.get("items", [])
        upcoming = [it for it in items if it.get("category") == "holiday" and it.get("date", "") > start.isoformat()]
        if not upcoming:
            return ""
        nearest = min(upcoming, key=lambda it: it["date"])
        holiday_date = datetime.fromisoformat(nearest["date"]).date()
        days_left = (holiday_date - start).days
        name = nearest.get("hebrew", nearest.get("title", ""))
        return f"🎉 **עד {name}:** {days_left} ימים"
    except Exception as e:
        log.error(f"haredi_updates: כשל בחישוב ימים לחג הבא: {e}")
        return ""


def build_daily_message() -> str:
    """מרכיב הודעה יומית אחת. אם מקור נכשל, הוא פשוט לא מופיע."""
    sections = [
        get_next_holiday_text(),
        get_fast_times_text(),
        get_candle_lighting_text(),
        get_zmanim_text(),
        get_daf_yomi_text(),
        get_parasha_text(),
        get_omer_or_roshchodesh_text(),
        get_molad_text(),
        get_yahrzeit_text(),
    ]
    sections = [s for s in sections if s]
    if not sections:
        return ""
    divider = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
    header = f"📅✨ **עדכון יומי** ✨\n{divider}"
    return f"{header}\n\n" + f"\n\n{divider}\n\n".join(sections)
