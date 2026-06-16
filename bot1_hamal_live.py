import feedparser
import requests
import time
import re
import random
import logging
import os
import urllib3
from datetime import datetime, timezone, timedelta

# ביטול התראות SSL (חשוב לסביבות מסוננות כמו נטפרי)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ניסיון ייבוא של ShabbatManager - אם חסר, המערכת תתריע
try:
    from shabbat import ShabbatManager
except ImportError:
    print("❌ שגיאה: קובץ shabbat.py חסר בתיקייה!")
    class ShabbatManager: # מחלקת דמי למניעת קריסה מיידית
        def is_shabbat(self): return False
        def should_send_shavua_tov(self): return False
        def should_send_shabbat_shalom(self): return False

# ============================================================
# הגדרות מערכת
# ============================================================
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

TARGET_URLS = [
    "https://new0040005.duckdns.org/api/import/post",
    "https://new0040000.duckdns.org/api/import/post"
]
API_SECRET_KEY = "k9f2sh392zh32_secure_random_key"

APPROVED_LINK_SITES = ["אבו עלי אקספרס", "NZIV", "כל רגע", "המחדש", "רדיו קול חי", "רדיו קול ברמה"]

SOURCE_DISPLAY = {
    "אבו עלי אקספרס": "🟢 אבו עלי אקספרס",
    "NZIV":            "🟤 NZIV",
    "כל רגע":         "🩵 כל רגע",
    "המחדש":           "🩶 המחדש",
    "רדיו קול חי":    "🟡 רדיו קול חי",
    "רדיו קול ברמה":  "🟠 רדיו קול ברמה",
}

BANNED_WORDS = ["זמר", "סלבס", "כדורגל", "אינסטגרם", "בידור", "להטב", "האח הגדול"] # רשימה מקוצרת לדוגמה

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
            # verify=False פותר בעיות חיבור בנטפרי/SSL
            res = requests.post(url, json=payload, headers=headers, timeout=10, verify=False)
            if res.status_code == 200:
                print(f"✅ הצלחה: נשלח ל-{url.split('.')[-3]}")
            else:
                print(f"⚠️ שגיאה ב-{url.split('.')[-3]}: סטטוס {res.status_code}")
        except Exception as e:
            log.error(f"קריסה בשליחה ל-{url}: {e}")
            print(f"❌ נכשל לשלוח ל-{url}")

def run():
    sb = ShabbatManager()
    print(f"🚀 בוט חמ\"ל מופעל | {len(SOURCES)} מקורות | שולח לשני ערוצים")

    while True:
        now = datetime.now()

        # בדיקת שבת
        if sb.is_shabbat():
            print(f"🕯️ שבת כעת - הבוט בהשהיה...")
            time.sleep(600)
            continue

        sources = list(SOURCES)
        random.shuffle(sources)

        for src in sources:
            try:
                # שימוש ב-headers כדי לדמות דפדפן (מונע חסימות)
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
                    
                    # שליחה לשני הערוצים
                    send_to_targets(msg, display, link)
                    
                    posted_links.add(entry.link)
                    if len(posted_links) > 1000: posted_links.clear()
                    time.sleep(2)

            except Exception as e:
                log.error(f"שגיאה במקור {src['name']}: {e}")

        time.sleep(30) # המתנה בין סבבים

if __name__ == "__main__":
    run()