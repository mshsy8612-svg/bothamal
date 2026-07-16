"""
תוכן תורני קצר לערוץ ייעודי: זמני הלכה + דף יומי (בשימוש חוזר מ-haredi_updates.py)
ובנוסף פתגם/משנה קצרים מפרקי אבות (טקסט עתיק, נחלת הכלל) שמתחלפים לפי חצי-השעה.
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from haredi_updates import get_zmanim_text, get_daf_yomi_text

log = logging.getLogger("bot1")
IL_TZ = ZoneInfo("Asia/Jerusalem")

# מבחר קצר מפרקי אבות - טקסט עתיק ונחלת הכלל, כל פריט קצר ומצוטט עם מקור.
# אפשר וכדאי להרחיב את הרשימה בהמשך.
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
    ("כל ישראל יש להם חלק לעולם הבא", "פרקי אבות פרק י, משנה א (סוף מסכת סנהדרין)"),
]


def get_dvar_torah_text() -> str:
    try:
        # מתחלף כל חצי שעה - שני slots ביום * 24 שעות = 48, מסתובב על הרשימה
        now = datetime.now(IL_TZ)
        slot = now.hour * 2 + (1 if now.minute >= 30 else 0)
        quote, source = PIRKEI_AVOT_QUOTES[slot % len(PIRKEI_AVOT_QUOTES)]
        return f'📖 **פתגם מפרקי אבות**\n"{quote}"\n_{source}_'
    except Exception as e:
        log.error(f"torah_updates: כשל בבניית דבר תורה: {e}")
        return ""


def build_torah_message() -> str:
    """מרכיב הודעה תורנית: זמני הלכה + דף יומי + פתגם מפרקי אבות. אם מקור נכשל - פשוט לא מופיע."""
    sections = [get_dvar_torah_text(), get_zmanim_text(), get_daf_yomi_text()]
    sections = [s for s in sections if s]
    if not sections:
        return ""
    divider = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
    header = f"📖✨ **פינת תורה** ✨\n{divider}"
    return f"{header}\n\n" + f"\n\n{divider}\n\n".join(sections)
