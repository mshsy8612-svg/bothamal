"""
עדכון יומי (לא שעתי!) עם תוכן רלוונטי לציבור החרדי:
זמנים הלכתיים, דף יומי, פרשת השבוע, ספירת העומר / ראש חודש, ויארצייט.
מקור: Hebcal.com (API חינמי, ללא מפתח). ראו https://www.hebcal.com/home/developer-apis
"""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

log = logging.getLogger("bot1")
IL_TZ = ZoneInfo("Asia/Jerusalem")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; bothamal-bot/1.0)"}


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
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
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


def _get_zmanim_raw(lat: float, lon: float):
    """שולף את מילון הזמנים הגולמי (times) מ-Hebcal לפי קואורדינטות. מחזיר None בכשל."""
    url = (
        "https://www.hebcal.com/zmanim?cfg=json"
        f"&latitude={lat}&longitude={lon}&tzid=Asia/Jerusalem&date={_today_str()}"
    )
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()["times"]


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
# זמנים הלכתיים - עיר ראשית עם כל הפירוט (רשימה) + שאר הערים בטבלה קטנה ונקייה (3 עמודות בלבד)
# ══════════════════════════════════════════════════
def get_zmanim_text() -> str:
    if not ZMANIM_CITIES:
        return ""
    primary = ZMANIM_CITIES[0]
    lines = []
    date_str = _get_today_dates_str()

    # עיר ראשית - כל הזמנים, כרשימה (לא טבלה - זה מה שהתקבל הכי טוב)
    try:
        t = _get_zmanim_raw(primary["lat"], primary["lon"])

        def g(*keys):
            for k in keys:
                if k in t:
                    return _fmt_time(t[k])
            return None

        rows = [(full, g(*keys)) for _, keys, full in ZMAN_COLUMNS]
        rows = [(name, val) for name, val in rows if val]
        if rows:
            lines.append(f"🕍 **זמני היום ({primary['name']})**")
            lines.append(f"📅 **{date_str}**")
            lines += [f"• {name}: {val}" for name, val in rows]
    except Exception as e:
        log.error(f"haredi_updates: כשל בשליפת זמנים ל-{primary['name']}: {e}")

    # שאר הערים - כל 10 הזמנים, באותה טבלה כמו העיר הראשית
    compact_cols = ZMAN_COLUMNS
    table_rows = []
    for city in ZMANIM_CITIES:
        try:
            t = _get_zmanim_raw(city["lat"], city["lon"])

            def g(*keys):
                for k in keys:
                    if k in t:
                        return _fmt_time(t[k])
                return "--"

            values = [g(*keys) for _, keys, _ in compact_cols]
            table_rows.append((city["name"], values))
        except Exception as e:
            log.error(f"haredi_updates: כשל בשליפת זמנים ל-{city['name']}: {e}")

    if table_rows:
        headers = ["עיר"] + [h for h, _, _ in compact_cols]
        md_lines = [
            "| " + " | ".join(headers) + " |",
            "|" + "|".join(["---"] * len(headers)) + "|",
        ]
        for name, values in table_rows:
            md_lines.append("| " + " | ".join([name] + values) + " |")

        if lines:
            lines.append("")
        lines.append("🌆 **ערים נוספות**")
        lines.append("")
        lines.append("\n".join(md_lines))

    return "\n".join(lines)


# ══════════════════════════════════════════════════
# דף יומי
# ══════════════════════════════════════════════════
def get_daf_yomi_text() -> str:
    try:
        d = _today_str()
        url = f"https://www.hebcal.com/hebcal?cfg=json&v=1&F=on&start={d}&end={d}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        items = r.json().get("items", [])
        daf = next((it for it in items if it.get("category") == "dafyomi"), None)
        if not daf:
            return ""
        return f"📖 **דף יומי:** {daf.get('hebrew', daf.get('title', ''))}"
    except Exception as e:
        log.error(f"haredi_updates: כשל בשליפת דף יומי: {e}")
        return ""


# ══════════════════════════════════════════════════
# פרשת השבוע
# ══════════════════════════════════════════════════
def get_parasha_text() -> str:
    try:
        start = datetime.now(IL_TZ).date()
        end = start + timedelta(days=8)  # מבטיח שבת אחת לפחות בטווח
        url = (
            "https://www.hebcal.com/hebcal?cfg=json&v=1&s=on&i=on"
            f"&start={start.isoformat()}&end={end.isoformat()}"
        )
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        items = r.json().get("items", [])
        parasha = next((it for it in items if it.get("category") == "parashat"), None)
        if not parasha:
            return ""
        return f"📜 **פרשת השבוע:** {parasha.get('hebrew', parasha.get('title', ''))}"
    except Exception as e:
        log.error(f"haredi_updates: כשל בשליפת פרשת השבוע: {e}")
        return ""


# ══════════════════════════════════════════════════
# ספירת העומר / ראש חודש (מוצג רק כשרלוונטי)
# ══════════════════════════════════════════════════
def get_omer_or_roshchodesh_text() -> str:
    try:
        d = _today_str()
        url = f"https://www.hebcal.com/hebcal?cfg=json&v=1&o=on&nx=on&start={d}&end={d}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        items = r.json().get("items", [])
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
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
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
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        items = r.json().get("items", [])
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
        get_zmanim_text(),
        get_daf_yomi_text(),
        get_parasha_text(),
        get_omer_or_roshchodesh_text(),
        get_yahrzeit_text(),
        get_next_holiday_text(),
    ]
    sections = [s for s in sections if s]
    if not sections:
        return ""
    divider = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
    header = f"📅✨ **עדכון יומי** ✨\n{divider}"
    return f"{header}\n\n" + f"\n\n{divider}\n\n".join(sections)
