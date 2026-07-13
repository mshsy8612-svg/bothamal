import math
import json
import logging
import urllib.request
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo

IL_TZ = ZoneInfo("Asia/Jerusalem")
log = logging.getLogger("bot1")

# ══════════════════════════════════════════════════
# הגדרת ערים ומנהגים
# ══════════════════════════════════════════════════
CITIES = [
    {"name": "ירושלים",       "id": 281184,  "lat": 31.7683, "lon": 35.2137, "standard": 40, "show_split": False},
    {"name": "בני ברק",       "id": 293253,  "lat": 32.0833, "lon": 34.8333, "standard": 20, "show_split": True},
    {"name": "אלעד",          "id": 295530,  "lat": 32.0500, "lon": 34.9500, "standard": 20, "show_split": True},
    {"name": "מודיעין עילית", "id": 283015,  "lat": 31.9333, "lon": 35.0500, "standard": 20, "show_split": True},
    {"name": "ביתר עילית",    "id": 8199964, "lat": 31.6972, "lon": 35.1128, "standard": 20, "show_split": True},
    {"name": "עמנואל",        "id": 293690,  "lat": 32.1667, "lon": 35.0667, "standard": 20, "show_split": True},
    {"name": "בית שמש",       "id": 293100,  "lat": 31.7500, "lon": 35.0000, "standard": 30, "show_split": False},
    {"name": "צפת",           "id": 293206,  "lat": 32.9646, "lon": 35.4961, "standard": 30, "show_split": False},
    {"name": "תל אביב",       "id": 293397,  "lat": 32.0667, "lon": 34.7667, "standard": 20, "show_split": False},
    {"name": "חיפה",          "id": 294801,  "lat": 32.8000, "lon": 34.9833, "standard": 20, "show_split": False},
    {"name": "פתח תקווה",     "id": 293248,  "lat": 32.0833, "lon": 34.8833, "standard": 20, "show_split": False},
    {"name": "אשדוד",         "id": 295629,  "lat": 31.8000, "lon": 34.6500, "standard": 20, "show_split": False},
    {"name": "באר שבע",       "id": 295530,  "lat": 31.2500, "lon": 34.7833, "standard": 20, "show_split": False},
    {"name": "נתניה",         "id": 293822,  "lat": 32.3333, "lon": 34.8500, "standard": 20, "show_split": False},
]

BASE_CITY = next(c for c in CITIES if c["name"] == "ירושלים")
HAVDALAH_MIN = 42

class ShabbatManager:
    def __init__(self):
        self._cache = {}
        self._use_api = True

    def _fetch(self, geoname_id: int, offset: int):
        url = f"https://www.hebcal.com/shabbat?cfg=json&geonameid={geoname_id}&m={HAVDALAH_MIN}&b={offset}&M=on"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NewsBot/1.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            log.error(f"shabbat.py: כשל בשליפת זמנים ל-geonameid={geoname_id}: {e}")
            return None

    def get_times(self, city: dict, offset: int) -> dict:
        data = self._fetch(city["id"], offset)
        res = {"candles": None, "havdalah": None, "yomtov": False, "name": "שבת"}
        if data:
            for item in data.get("items", []):
                cat = item.get("category", "")
                dt_str = item.get("date", "")
                try:
                    dt = datetime.fromisoformat(dt_str).astimezone(IL_TZ).replace(tzinfo=None)
                except Exception as e:
                    log.error(f"shabbat.py: כשל בפענוח תאריך '{dt_str}': {e}")
                    continue
                if cat == "candles":
                    res["candles"] = dt
                    title = item.get("title", "")
                    if any(x in title for x in ["Rosh Hashana", "Sukkot", "Pesach", "Shavuot"]):
                        res["yomtov"] = True
                        res["name"] = title.replace("Candle lighting: ", "").strip()
                elif cat == "havdalah": res["havdalah"] = dt
        return res

    def get_sunset(self, city: dict) -> str:
        t = self.get_times(city, city["standard"])
        if t["candles"]:
            sunset = t["candles"] + timedelta(minutes=city["standard"])
            return sunset.strftime("%H:%M")
        return "--:--"

    def is_shabbat(self) -> bool:
        t = self.get_times(BASE_CITY, 40)
        if not t["candles"] or not t["havdalah"]: return False
        now = datetime.now(IL_TZ).replace(tzinfo=None)
        # שבת מתחילה 40 דקות לפני שקיעה (= זמן ההדלקה) ומסתיימת בצאת השבת
        return t["candles"] <= now <= t["havdalah"]

    def should_send_shabbat_shalom(self) -> bool:
        t = self.get_times(BASE_CITY, 40)
        if not t["candles"]: return False
        now = datetime.now(IL_TZ).replace(tzinfo=None)
        # שלח ברכה רק בחלון של 60 דקות לפני כניסת שבת (לא בשבת עצמה!)
        diff = (t["candles"] - now).total_seconds()
        return 0 < diff < 3600

    def should_send_shavua_tov(self) -> bool:
        t = self.get_times(BASE_CITY, 40)
        if not t["havdalah"]: return False
        diff = (datetime.now(IL_TZ).replace(tzinfo=None) - t["havdalah"]).total_seconds()
        return 0 < diff < 3600

    def get_greeting(self) -> str:
        base = self.get_times(BASE_CITY, 40)
        jlm_sun = self.get_sunset(BASE_CITY)
        
        # בניית ההודעה
        msg = "🕯️ **שבת שלום לכל בית ישראל!**\n\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "📻 מערכת החדשות מאחלת שבת שלום ומבורכת.\n\n"
        
        msg += "🕯️ **זמני הדלקת נרות:**\n\n"
        
        # ירושלים - 40 דקות
        msg += f"📍 **ירושלים (40 דק' לפני שקיעה):**\n"
        msg += f"🌅 שקיעה: {jlm_sun} | 🕯️ הדלקה: **{base['candles'].strftime('%H:%M')}**\n\n"

        # ערים עם פיצול - 30/20 דקות
        msg += "⏰ **לנוהגים 30 דק' | לנוהגים 20 דק':**\n"
        ref_time = base['candles']
        for c in [city for city in CITIES if city.get("show_split")]:
            t30 = (ref_time + timedelta(minutes=10)).strftime('%H:%M')
            t20 = (ref_time + timedelta(minutes=20)).strftime('%H:%M')
            msg += f"🔹 **{c['name']}:** {t30} | {t20}\n"

        # ערים רגילות - 20 או 30 דקות
        msg += "\n⏰ **ערים נוספות:**\n"
        for c in [city for city in CITIES if not city.get("show_split") and city["name"] != "ירושלים"]:
            t = self.get_times(c, c["standard"])["candles"]
            if t:
                msg += f"• **{c['name']}:** {t.strftime('%H:%M')}\n"

        msg += f"\n✨ **צאת השבת (ירושלים): {base['havdalah'].strftime('%H:%M')}**\n"
        msg += "(_Hebcal API 🌐_)\n\n"
        msg += "הערוץ ישוב לשידור לאחר צאת השבת.\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "🇮🇱 **שבת שלום ומנוחה לכל עם ישראל.**"

        return msg

    def get_shavua_tov_greeting(self, shabbat_summary: str = "") -> str:
        msg  = "✨ **שבוע טוב ומבורך לכל בית ישראל!**\n\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        msg += "📻 **מערכת החדשות חוזרת לשידור.**\n\n"
        if shabbat_summary:
            msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            msg += "📰 **סיכום חדשות השבת:**\n\n"
            msg += shabbat_summary.strip() + "\n\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "🇮🇱 **שבוע של בשורות טובות.**"
        return msg

    def get_shabbat_summary_from_api(self, api_url: str, api_key: str) -> str:
        """
        שולף את 5 הפוסטים האחרונים מהשבת ובונה מהם סיכום.
        """
        import urllib.parse
        try:
            req = urllib.request.Request(
                api_url.replace("/api/import/post", "/api/posts?limit=20"),
                headers={"X-API-Key": api_key, "User-Agent": "NewsBot/1.0"}
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                posts = json.loads(r.read().decode())
            t = self.get_times(BASE_CITY, 40)
            if not t["candles"] or not t["havdalah"]:
                return ""
            shabbat_posts = []
            for p in posts:
                try:
                    dt_str = p.get("created_at") or p.get("timestamp") or ""
                    dt = datetime.fromisoformat(dt_str.replace("Z","")).replace(tzinfo=None)
                    if t["candles"] <= dt <= t["havdalah"]:
                        text = p.get("text","").strip()
                        if text:
                            shabbat_posts.append(text)
                except: continue
            if not shabbat_posts:
                return ""
            # לקחת 5 פוסטים בלבד
            lines = []
            for i, post in enumerate(shabbat_posts[-5:], 1):
                first_line = post.split("\n")[0][:120]
                lines.append(f"{i}. {first_line}")
            return "\n".join(lines)
        except Exception as e:
            log.error(f"shabbat.py: כשל בשליפת סיכום פוסטי שבת: {e}")
            return ""

    def get_shabbat_greeting(self): return self.get_greeting()
