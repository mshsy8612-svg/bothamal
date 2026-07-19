"""
קאש פשוט בזיכרון (בתהליך) ל-GET+JSON, כדי לצמצם קריאות רשת חוזרות ל-Hebcal/Sefaria.
לא מתאים לנתונים שמשתנים תוך כדי היום (כמו "עכשיו X מעלות") - רק לדברים יציבים
כמו זמנים הלכתיים, דף יומי, פרשה וכו', שלא משתנים בין קריאה לקריאה באותה שעה/יום.
"""
import time
import logging

import requests

log = logging.getLogger("bot1")

_cache = {}  # key -> (timestamp, data)


def cached_get_json(url: str, ttl: int = 600, headers: dict = None, timeout: int = 10):
    """GET + json() עם קאש. ttl בשניות. זורק חריגה אם הבקשה נכשלת ואין קאש קודם."""
    now = time.time()
    entry = _cache.get(url)
    if entry and (now - entry[0]) < ttl:
        return entry[1]
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    _cache[url] = (now, data)
    return data


def clear_cache():
    _cache.clear()
