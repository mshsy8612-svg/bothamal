import feedparser
import requests
import time
import re
import random
import logging
import os
import urllib3
import threading
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from http.server import HTTPServer, BaseHTTPRequestHandler

IL_TZ = ZoneInfo("Asia/Jerusalem")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from shabbat import ShabbatManager
except ImportError:
    print("❌ שגיאה: קובץ shabbat.py חסר!")
    class ShabbatManager:
        def is_shabbat(self): return False
        def should_send_shavua_tov(self): return False
        def should_send_shabbat_shalom(self): return False

try:
    from hourly_updates import build_hourly_message
except ImportError:
    print("❌ שגיאה: קובץ hourly_updates.py חסר!")
    def build_hourly_message(): return ""

try:
    from haredi_updates import build_daily_message
except ImportError:
    print("❌ שגיאה: קובץ haredi_updates.py חסר!")
    def build_daily_message(): return ""

try:
    from torah_updates import build_torah_message
except ImportError:
    print("❌ שגיאה: קובץ torah_updates.py חסר!")
    def build_torah_message(): return ""

LOG_DIR  = "logs"
LOG_FILE = os.path.join(LOG_DIR, "bot1.log")

def setup_logger():
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger("bot1")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(fh)
    return logger

log = setup_logger()

_DEFAULT_TARGET_URLS = [
    "https://new0040005.duckdns.org/api/import/post",
    "https://new0040000.duckdns.org/api/import/post",
    "https://my-channel-w1nx.onrender.com/api/import/post"
]
_DEFAULT_API_SECRET_KEY = "k9f2sh392zh32_secure_random_key"

# ניתן לדרוס את שני אלה עם משתני סביבה בלי לגעת בקוד:
#   TARGET_URLS=https://a.com/api/import/post,https://b.com/api/import/post
#   API_SECRET_KEY=xxxxx
# אם משתני הסביבה לא מוגדרים, הבוט ממשיך לעבוד עם הערכים המקוריים (שום שינוי בהתנהגות).
_env_targets = os.environ.get("TARGET_URLS")
TARGET_URLS = [u.strip() for u in _env_targets.split(",") if u.strip()] if _env_targets else _DEFAULT_TARGET_URLS
API_SECRET_KEY = os.environ.get("API_SECRET_KEY", _DEFAULT_API_SECRET_KEY)

if API_SECRET_KEY == _DEFAULT_API_SECRET_KEY:
    print("⚠️  אזהרה: משתמש במפתח API בררת המחדל (חשוף בקוד). מומלץ להגדיר משתנה סביבה API_SECRET_KEY ולהחליף את המפתח.")

# ערוץ נפרד ל"פינת תורה" - לא קשור בכלל ל-TARGET_URLS למעלה.
# ⚠️ המפתח כאן זהה למפתח בררת המחדל החשוף - מומלץ בחום להחליף אותו (גם בצד השרת של הערוץ הזה עצמו)!
_DEFAULT_TORAH_CHANNEL_URL = "https://entertainment-channel.onrender.com/api/import/post"
_DEFAULT_TORAH_API_KEY = "k9f2sh392zh32_secure_random_key"
TORAH_CHANNEL_URL = os.environ.get("TORAH_CHANNEL_URL", _DEFAULT_TORAH_CHANNEL_URL)
TORAH_API_KEY = os.environ.get("TORAH_API_KEY", _DEFAULT_TORAH_API_KEY)

APPROVED_LINK_SITES = ["אבו עלי אקספרס", "NZIV", "כל רגע", "המחדש", "רדיו קול חי", "רדיו קול ברמה"]

SOURCE_DISPLAY = {
    "אבו עלי אקספרס": "🟢 אבו עלי אקספרס",
    "NZIV":            "🟤 NZIV",
    "כל רגע":         "🩵 כל רגע",
    "המחדש":           "🩶 המחדש",
    "רדיו קול חי":    "🟡 רדיו קול חי",
    "רדיו קול ברמה":  "🟠 רדיו קול ברמה",
}

BANNED_WORDS = ["זמר", "סלבס", "כדורגל", "אינסטגרם", "בידור", "להטב", "האח הגדול"]

SOURCES = [
    {"name": "אבו עלי אקספרס", "url": "https://abualiexpress.com/feed/"},
    {"name": "NZIV",            "url": "https://nziv.net/feed/"},
    {"name": "כל רגע",         "url": "https://kore.co.il/rss"},
    {"name": "המחדש",          "url": "https://hm-news.co.il/category/flash/feed/"},
    {"name": "רדיו קול חי",    "url": "https://www.93fm.co.il/feed/"},
    {"name": "רדיו קול ברמה",  "url": "https://kol-barama.co.il/feed/"},
]

posted_links = set()

def clean_text(raw_html):
    if not raw_html: return ""
    text = re.sub(r'<[^>]*>|&nbsp;', ' ', raw_html)
    return ' '.join(text.split()).strip()

def is_safe(text):
    if not text or len(text) < 15: return False
    lower = text.lower()
    for word in BANNED_WORDS:
        if word in lower: return False
    return True

def send_to_targets(text, author, link=None):
    if link:
        text += f"\n\n🔗 [לכתבה המלאה]({link})"
    payload = {
        "text": text,
        "author": author,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    headers = {"X-API-Key": API_SECRET_KEY}
    for url in TARGET_URLS:
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=10, verify=False)
            if res.status_code == 200:
                print(f"✅ נשלח ל-{url.split('/')[2]}")
            else:
                print(f"⚠️ שגיאה ב-{url.split('/')[2]}: סטטוס {res.status_code}")
        except Exception as e:
            log.error(f"קריסה בשליחה ל-{url}: {e}")
            print(f"❌ קריסה בשליחה ל-{url}: {e}")

def send_to_torah_channel(text, author):
    """שליחה לערוץ התורני היחיד (entertainment-channel) - נפרד לגמרי מ-TARGET_URLS."""
    payload = {
        "text": text,
        "author": author,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    headers = {"X-API-Key": TORAH_API_KEY}
    try:
        res = requests.post(TORAH_CHANNEL_URL, json=payload, headers=headers, timeout=10, verify=False)
        if res.status_code == 200:
            print(f"✅ נשלח לערוץ התורני ({TORAH_CHANNEL_URL.split('/')[2]})")
        else:
            print(f"⚠️ שגיאה בערוץ התורני: סטטוס {res.status_code}")
    except Exception as e:
        log.error(f"קריסה בשליחה לערוץ התורני: {e}")
        print(f"❌ קריסה בשליחה לערוץ התורני: {e}")

def run_bot():
    sb = ShabbatManager()
    sent_shabbat_shalom_date = None
    sent_shavua_tov_date = None
    last_hourly_key = None  # (date, hour) של העדכון השעתי האחרון שנשלח
    last_daily_key = None   # (date, hour) של העדכון היומי (זמנים/דף יומי/פרשה) האחרון שנשלח
    last_torah_key = None   # (date, hour) של העדכון התורני האחרון שנשלח לערוץ הייעודי
    DAILY_UPDATE_HOURS = {6, 13, 20}  # 3 פעמים ביום: בוקר, צהריים, ערב
    print(f"🚀 בוט חמ\"ל מופעל | {len(SOURCES)} מקורות")
    while True:
        now = datetime.now(IL_TZ)
        today = now.date()

        hourly_key = (today, now.hour)
        if hourly_key != last_hourly_key and not sb.is_shabbat():
            try:
                msg = build_hourly_message()
                if msg:
                    send_to_targets(msg, "🕐 עדכון שעתי")
                    log.info("נשלח עדכון שעתי")
                    last_hourly_key = hourly_key  # רק בהצלחה - אחרת ננסה שוב בסבב הבא
                else:
                    log.error("עדכון שעתי: build_hourly_message החזיר ריק (כל המקורות נכשלו) - ינסה שוב בסבב הבא")
            except Exception as e:
                log.error(f"שגיאה בשליחת עדכון שעתי: {e}")
                print(f"❌ שגיאה בשליחת עדכון שעתי: {e}")

        # עדכון יומי (זמנים הלכתיים, דף יומי, פרשה, עומר/ר"ח, יארצייט) - 3 פעמים ביום (06:00, 13:00, 20:00)
        daily_key = (today, now.hour)
        if now.hour in DAILY_UPDATE_HOURS and daily_key != last_daily_key and not sb.is_shabbat():
            try:
                msg = build_daily_message()
                if msg:
                    send_to_targets(msg, "📅 עדכון יומי")
                    log.info("נשלח עדכון יומי")
                    last_daily_key = daily_key
                else:
                    log.error("עדכון יומי: build_daily_message החזיר ריק - ינסה שוב בסבב הבא")
            except Exception as e:
                log.error(f"שגיאה בשליחת עדכון יומי: {e}")
                print(f"❌ שגיאה בשליחת עדכון יומי: {e}")

        # פינת תורה (זמנים + דף יומי + פתגם מפרקי אבות) - כל שעה עגולה בלבד, לערוץ הייעודי. לא בשבת.
        torah_key = (today, now.hour)
        if torah_key != last_torah_key and not sb.is_shabbat():
            try:
                msg = build_torah_message()
                if msg:
                    send_to_torah_channel(msg, "📖 פינת תורה")
                    log.info("נשלח עדכון תורני לערוץ הייעודי")
                    last_torah_key = torah_key
                else:
                    log.error("פינת תורה: build_torah_message החזיר ריק - ינסה שוב בסבב הבא")
            except Exception as e:
                log.error(f"שגיאה בשליחת פינת תורה: {e}")
                print(f"❌ שגיאה בשליחת פינת תורה: {e}")

        if sb.should_send_shabbat_shalom() and sent_shabbat_shalom_date != today:
            try:
                send_to_targets(sb.get_greeting(), "📻 מערכת")
                sent_shabbat_shalom_date = today
                log.info("נשלחה ברכת שבת שלום")
            except Exception as e:
                log.error(f"שגיאה בשליחת ברכת שבת שלום: {e}")

        if sb.is_shabbat():
            print("🕯️ שבת כעת - הבוט בהשהיה...")
            time.sleep(600)
            continue

        if sb.should_send_shavua_tov() and sent_shavua_tov_date != today:
            try:
                send_to_targets(sb.get_shavua_tov_greeting(), "📻 מערכת")
                sent_shavua_tov_date = today
                log.info("נשלחה ברכת שבוע טוב")
            except Exception as e:
                log.error(f"שגיאה בשליחת ברכת שבוע טוב: {e}")

        sources = list(SOURCES)
        random.shuffle(sources)
        for src in sources:
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(src["url"], timeout=10, verify=False, headers=headers)
                feed = feedparser.parse(response.content)
                for entry in feed.entries[:3]:
                    if entry.link in posted_links:
                        continue
                    title = clean_text(entry.get('title', ''))
                    if not is_safe(title):
                        continue
                    display = SOURCE_DISPLAY.get(src['name'], src['name'])
                    msg = f"⚡ **מבזק** | {display}\n\n🔴 **{title}**"
                    link = entry.link if src['name'] in APPROVED_LINK_SITES else None
                    send_to_targets(msg, display, link)
                    posted_links.add(entry.link)
                    if len(posted_links) > 1000:
                        posted_links.clear()
                    time.sleep(2)
            except Exception as e:
                log.error(f"שגיאה במקור {src['name']}: {e}")
                print(f"❌ שגיאה במקור {src['name']}: {e}")
        time.sleep(30)

class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is running!")
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), KeepAliveHandler)
    print(f"🌐 שרת keep-alive על פורט {port}")
    server.serve_forever()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    run_server()
