"""
שליפת טקסט מלא של כתבה, במקום רק כותרת.
סדר עדיפות:
1. אם ה-RSS עצמו כולל תוכן מלא (content:encoded) - להשתמש בזה, הכי אמין וללא בקשת רשת נוספת.
2. אם יש summary/description ארוך יותר מהכותרת - להשתמש בזה.
3. אחרת לגשת לעמוד הכתבה עצמו ולנסות לחלץ טקסט בצורה גנרית (לא ספציפי לאתר).
"""
import logging
import re

import requests
from bs4 import BeautifulSoup

log = logging.getLogger("bot1")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
MAX_ARTICLE_CHARS = 3500  # תקרה כדי לא לשלוח הודעות ענקיות בלתי סבירות

# תגים שסביר שמכילים את גוף הכתבה באתרי וורדפרס עבריים נפוצים
CONTENT_SELECTORS = [
    "div.entry-content", "div.post-content", "div.td-post-content",
    "div.article-content", "div.content-inner", "div.single-content",
    "article",
]


def _clean(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]*>|&nbsp;", " ", raw_html)
    return " ".join(text.split()).strip()


def _from_feed_entry(entry) -> str:
    """מנסה לשלוף טקסט מלא ישירות מה-RSS entry (content:encoded או summary)."""
    try:
        content_list = entry.get("content")
        if content_list:
            text = _clean(content_list[0].get("value", ""))
            if len(text) > 200:
                return text
    except Exception:
        pass
    summary = _clean(entry.get("summary", ""))
    return summary


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
                text = " ".join(p for p in paragraphs if len(p) > 20)
                if len(text) > 200:
                    return text
        return ""
    except Exception as e:
        log.error(f"article_extractor: כשל בשליפת עמוד הכתבה {url}: {e}")
        return ""


def get_full_article_text(entry, url: str, title: str) -> str:
    """מחזיר את הטקסט המלא הכי טוב שאפשר להשיג, או מחרוזת ריקה אם לא הצליח (ואז נציג רק כותרת, כמו קודם)."""
    text = _from_feed_entry(entry)
    if len(text) <= len(title) + 20:  # קצר מדי / זהה לכותרת - ננסה את העמוד עצמו
        page_text = _from_article_page(url)
        if page_text:
            text = page_text
    if not text:
        return ""
    if len(text) > MAX_ARTICLE_CHARS:
        text = text[:MAX_ARTICLE_CHARS].rsplit(" ", 1)[0] + "..."
    return text
