"""
עדכון שעתי משולב: מזג אוויר, שערי מטבע, קריפטו.
כל המקורות כאן חינמיים ולא דורשים API key.
"""
import logging
import requests

log = logging.getLogger("bot1")

# ערים לעדכון מזג אוויר (משתמש באותם קואורדינטות כמו shabbat.py)
WEATHER_CITIES = [
    {"name": "ירושלים",  "lat": 31.7683, "lon": 35.2137},
    {"name": "תל אביב",  "lat": 32.0667, "lon": 34.7667},
    {"name": "חיפה",     "lat": 32.8000, "lon": 34.9833},
    {"name": "באר שבע",  "lat": 31.2500, "lon": 34.7833},
]

# קודי מזג אוויר (WMO) -> תיאור + אימוג'י, לפי Open-Meteo
WEATHER_CODES = {
    0: ("בהיר", "☀️"), 1: ("בהיר בעיקר", "🌤️"), 2: ("מעונן חלקית", "⛅"), 3: ("מעונן", "☁️"),
    45: ("ערפל", "🌫️"), 48: ("ערפל קפוא", "🌫️"),
    51: ("טפטוף קל", "🌦️"), 53: ("טפטוף", "🌦️"), 55: ("טפטוף חזק", "🌦️"),
    61: ("גשם קל", "🌧️"), 63: ("גשם", "🌧️"), 65: ("גשם חזק", "🌧️"),
    71: ("שלג קל", "🌨️"), 73: ("שלג", "🌨️"), 75: ("שלג כבד", "❄️"),
    80: ("ממטרים קלים", "🌦️"), 81: ("ממטרים", "🌧️"), 82: ("ממטרים חזקים", "⛈️"),
    95: ("סופת רעמים", "⛈️"),
}

CURRENCIES = ["USD", "EUR", "GBP"]
CRYPTO = ["bitcoin", "ethereum"]


def get_weather_text() -> str:
    lines = ["🌤️ **מזג אוויר עכשיו:**"]
    ok = False
    for city in WEATHER_CITIES:
        try:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                f"?latitude={city['lat']}&longitude={city['lon']}"
                "&current=temperature_2m,weather_code&timezone=Asia%2FJerusalem"
            )
            r = requests.get(url, timeout=8)
            r.raise_for_status()
            data = r.json()["current"]
            temp = round(data["temperature_2m"])
            desc, emoji = WEATHER_CODES.get(data["weather_code"], ("", "🌡️"))
            lines.append(f"{emoji} **{city['name']}:** {temp}°C {desc}")
            ok = True
        except Exception as e:
            log.error(f"hourly_updates: כשל במזג אוויר עבור {city['name']}: {e}")
    return "\n".join(lines) if ok else ""


def get_currency_text() -> str:
    lines = ["💱 **שערי מטבע (מול ₪):**"]
    ok = False
    for cur in CURRENCIES:
        try:
            url = f"https://api.frankfurter.app/latest?from={cur}&to=ILS"
            r = requests.get(url, timeout=8)
            r.raise_for_status()
            rate = r.json()["rates"]["ILS"]
            lines.append(f"💵 **{cur}:** {rate:.2f} ₪")
            ok = True
        except Exception as e:
            log.error(f"hourly_updates: כשל בשער מטבע {cur}: {e}")
    return "\n".join(lines) if ok else ""


def get_crypto_text() -> str:
    lines = ["₿ **קריפטו:**"]
    ok = False
    try:
        ids = ",".join(CRYPTO)
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd,ils"
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
        names = {"bitcoin": "Bitcoin (BTC)", "ethereum": "Ethereum (ETH)"}
        for cid in CRYPTO:
            if cid in data:
                usd = data[cid].get("usd")
                ils = data[cid].get("ils")
                lines.append(f"🔸 **{names.get(cid, cid)}:** ${usd:,.0f} | {ils:,.0f} ₪")
                ok = True
    except Exception as e:
        log.error(f"hourly_updates: כשל בשליפת קריפטו: {e}")
    return "\n".join(lines) if ok else ""


def build_hourly_message() -> str:
    """מרכיב הודעה אחת משולבת. אם מקור מסוים נכשל, הוא פשוט לא מופיע - שאר המקורות עדיין נשלחים."""
    sections = [get_weather_text(), get_currency_text(), get_crypto_text()]
    sections = [s for s in sections if s]
    if not sections:
        return ""
    msg = "🕐 **עדכון שעתי**\n\n"
    msg += "\n\n".join(sections)
    return msg
