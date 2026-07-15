"""
עדכון שעתי משולב: מזג אוויר, שערי מטבע, קריפטו.
כל המקורות כאן חינמיים ולא דורשים API key.
"""
import logging
import requests

log = logging.getLogger("bot1")

# חלק מה-APIs חוסמים בקשות עם ה-User-Agent ברירת המחדל של requests
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; bothamal-bot/1.0)"}

# ערים לעדכון מזג אוויר (משתמש באותם קואורדינטות כמו shabbat.py)
WEATHER_CITIES = [
    {"name": "ירושלים",     "lat": 31.7683, "lon": 35.2137},
    {"name": "תל אביב",     "lat": 32.0667, "lon": 34.7667},
    {"name": "חיפה",        "lat": 32.8000, "lon": 34.9833},
    {"name": "באר שבע",     "lat": 31.2500, "lon": 34.7833},
    {"name": "מודיעין עילית", "lat": 31.9316, "lon": 35.0417},
    {"name": "אלעד",        "lat": 32.0505, "lon": 34.9505},
    {"name": "בית שמש",     "lat": 31.7463, "lon": 34.9887},
    {"name": "ביתר עילית",  "lat": 31.6976, "lon": 35.1194},
    {"name": "טבריה",       "lat": 32.7922, "lon": 35.5312},
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
    rows = []  # (name, now_temp, t_min, t_max, emoji)
    for city in WEATHER_CITIES:
        try:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                f"?latitude={city['lat']}&longitude={city['lon']}"
                "&current=temperature_2m"
                "&daily=temperature_2m_max,temperature_2m_min,weather_code"
                "&timezone=Asia%2FJerusalem&forecast_days=1"
            )
            r = requests.get(url, headers=HEADERS, timeout=8)
            r.raise_for_status()
            data = r.json()
            now_temp = round(data["current"]["temperature_2m"])
            daily = data["daily"]
            t_min = round(daily["temperature_2m_min"][0])
            t_max = round(daily["temperature_2m_max"][0])
            _, emoji = WEATHER_CODES.get(daily["weather_code"][0], ("", "🌡️"))
            rows.append((city["name"], now_temp, t_min, t_max, emoji))
        except Exception as e:
            log.error(f"hourly_updates: כשל במזג אוויר עבור {city['name']}: {e}")
    if not rows:
        return ""

    hottest = max(rows, key=lambda r: r[3])
    coldest = min(rows, key=lambda r: r[2])

    lines = [
        "🌦️ **תחזית מזג אוויר להיום**",
        f"🔥 הכי חם: **{hottest[0]}** ({hottest[3]}°)   ❄️ הכי קר: **{coldest[0]}** ({coldest[2]}°)",
        "━━━━━━━━━━━━━━━━━━",
    ]
    for name, now_temp, t_min, t_max, emoji in rows:
        lines.append(f"{emoji} **{name}:** {t_min}°–{t_max}°")
    return "\n".join(lines)


def get_currency_rates() -> dict:
    """קריאה יחידה במקום 3 נפרדות - פחות סיכוי לכשל חלקי. מחזיר {'USD': 3.65, 'EUR': 3.9, 'GBP': 4.6} או {}"""
    try:
        url = f"https://api.frankfurter.app/latest?from=ILS&to={','.join(CURRENCIES)}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        rates_from_ils = r.json()["rates"]  # כמה דולר/יורו/ליש"ט ב-1 ש"ח
        return {cur: 1 / rate for cur, rate in rates_from_ils.items() if rate}
    except Exception as e:
        log.error(f"hourly_updates: כשל בשליפת שערי מטבע: {e}")
        return {}


def get_currency_text(rates: dict) -> str:
    if not rates:
        return ""
    lines = ["💱 **שערי מטבע (מול ₪):**"]
    for cur in CURRENCIES:
        if cur in rates:
            lines.append(f"💵 **{cur}:** {rates[cur]:.2f} ₪")
    return "\n".join(lines) if len(lines) > 1 else ""


# סמלי מסחר לכל מטבע קריפטו
BINANCE_SYMBOLS = {"bitcoin": ("BTCUSDT", "Bitcoin (BTC)"), "ethereum": ("ETHUSDT", "Ethereum (ETH)")}
CRYPTOCOMPARE_SYMBOLS = {"bitcoin": ("BTC", "Bitcoin (BTC)"), "ethereum": ("ETH", "Ethereum (ETH)")}


def _get_price_binance(symbol: str) -> float:
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return float(r.json()["price"])


def _get_price_cryptocompare(symbol: str) -> float:
    url = f"https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USD"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return float(r.json()["USD"])


def get_crypto_text(usd_to_ils: float | None) -> str:
    """usd_to_ils: כמה ש"ח ב-1 דולר (כדי להציג גם בשקלים בלי קריאת API נוספת). אם None - יוצג רק דולר.
    מנסה קודם Binance, ואם זה נכשל (למשל חסימה גיאוגרפית משרתים בארה"ב) - נופל ל-CryptoCompare."""
    lines = ["₿ **שוק הקריפטו**"]
    ok = False
    for cid, (binance_symbol, display_name) in BINANCE_SYMBOLS.items():
        usd = None
        try:
            usd = _get_price_binance(binance_symbol)
        except Exception as e:
            log.error(f"hourly_updates: Binance נכשל עבור {display_name}: {e}")
            try:
                cc_symbol = CRYPTOCOMPARE_SYMBOLS[cid][0]
                usd = _get_price_cryptocompare(cc_symbol)
                log.info(f"hourly_updates: {display_name} נשלף בהצלחה דרך CryptoCompare (גיבוי)")
            except Exception as e2:
                log.error(f"hourly_updates: גם CryptoCompare נכשל עבור {display_name}: {e2}")
        if usd is not None:
            if usd_to_ils:
                lines.append(f"🔸  **{display_name}**  ·  ${usd:,.0f}  ({usd * usd_to_ils:,.0f} ₪)")
            else:
                lines.append(f"🔸  **{display_name}**  ·  ${usd:,.0f}")
            ok = True
    return "\n".join(lines) if ok else ""


def build_hourly_message() -> str:
    """מרכיב הודעה שעתית מעוצבת. כרגע רק מזג אוויר."""
    weather = get_weather_text()
    if not weather:
        return ""
    divider = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
    header = f"🕐✨ **עדכון שעתי** ✨\n{divider}"
    return f"{header}\n\n{weather}"
