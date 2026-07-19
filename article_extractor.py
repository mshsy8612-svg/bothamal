"""
שליפת טקסט מלא של כתבה, במקום רק כותרת.
סדר עדיפות:
1. אם ה-RSS עצמו כולל תוכן מלא (content:encoded) - להשתמש בזה, הכי אמין וללא בקשת רשת נוספת.
2. אם יש summary/description ארוך יותר מהכותרת - להשתמש בזה.
3. אחרת לגשת לעמוד הכתבה עצמו ולנסות לחלץ טקסט בצורה גנרית (לא ספציפי לאתר).

בכל שלב מנקים: ישויות HTML לא מפוענחות (&#8221; וכו'), "בונוס-אשפה" של תוספי RSS
נפוצים (The post ... appeared first on ..., אזהרות מקור וכו'), וקישורי מדיה גולמיים
שמככבים כטקסט חסר משמעות.
"""
import html
import logging
import re

import requests
from bs4 import BeautifulSoup

log = logging.getLogger("bot1")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
MAX_ARTICLE_CHARS = 3500  # תקרה כדי לא לשלוח הודעות ענקיות בלתי סבירות
MIN_REAL_CONTENT_CHARS = 150  # אם אחרי ניקוי נשאר פחות מזה - זה כנראה רק "אשפה", לא תוכן אמיתי

# תגים שסביר שמכילים את גוף הכתבה באתרי וורדפרס עבריים נפוצים
CONTENT_SELECTORS = [
    "div.entry-content", "div.post-content", "div.td-post-content",
    "div.article-content", "div.content-inner", "div.single-content",
    "article",
]

# "בונוס-אשפה" נפוץ שתוספי RSS/אגרגטורים מוסיפים אוטומטית - לא חלק מהכתבה עצמה
BOILERPLATE_PATTERNS = [
    r"The post .*? appeared first on .*?\.",
    r"מקור השיגור בבדיקה[^.]*\.",
    r"על פי מדיניות[^.]*\.",
]


def _strip_urls_and_boilerplate(text: str) -> str:
    for pattern in BOILERPLATE_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE | re.DOTALL)
    # קישורי מדיה/קבצים גולמיים שאין להם ערך כטקסט (mp4/mp3/jpg/png/pdf וכו')
    text = re.sub(r"https?://\S+\.(mp4|mp3|jpg|jpeg|png|gif|pdf|webp)\S*", " ", text, flags=re.IGNORECASE)
    # כל קישור גולמי אחר שנשאר בתוך הטקסט (לא רלוונטי כטקסט רץ, הקישור לכתבה כבר מתווסף בנפרד)
    text = re.sub(r"https?://\S+", " ", text)
    return text


def _clean(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]*>|&nbsp;", " ", raw_html)
    text = html.unescape(text)  # &#8221; -> ” וכו'
    text = _strip_urls_and_boilerplate(text)
    return " ".join(text.split()).strip()


def _from_feed_entry(entry) -> str:
    """מנסה לשלוף טקסט מלא ישירות מה-RSS entry (content:encoded או summary)."""
    try:
        content_list = entry.get("content")
        if content_list:
            text = _clean(content_list[0].get("value", ""))
            if len(text) > MIN_REAL_CONTENT_CHARS:
                return text
    except Exception:
        pass
    return _clean(entry.get("summary", ""))


def _from_article_page(url: str) -> str:
    """שולף ומנסה לחלץ את גוף הכתבה מעמוד ה-HTML עצמו, בצורה גנרית (לא ספציפי לאתר)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        for selector in CONTENT_SELECTORS:
            el = soup.select_one(selector)
            if el:
                paragraphs = [p.get_text(" ", strip=True) for p in el.find_all("p")]
                text = _clean(" ".join(p for p in paragraphs if len(p) > 20))
                if len(text) > MIN_REAL_CONTENT_CHARS:
                    return text
        return ""
    except Exception as e:
        log.error(f"article_extractor: כשל בשליפת עמוד הכתבה {url}: {e}")
        return ""


def get_full_article_text(entry, url: str, title: str) -> str:
    """מחזיר את הטקסט המלא הכי טוב שאפשר להשיג, או מחרוזת ריקה אם לא הצליח
    (ואז נציג רק כותרת, כמו קודם) - כולל אם כל מה שנמצא זה רק 'אשפה' בלי תוכן אמיתי."""
    text = _from_feed_entry(entry)
    if len(text) <= max(len(title) + 20, MIN_REAL_CONTENT_CHARS):
        page_text = _from_article_page(url)
        if page_text:
            text = page_text
    if len(text) < MIN_REAL_CONTENT_CHARS:
        return ""
    if len(text) > MAX_ARTICLE_CHARS:
        text = text[:MAX_ARTICLE_CHARS].rsplit(" ", 1)[0] + "..."
    return text
