from mcp.server.fastmcp import FastMCP
import requests, feedparser, random

mcp = FastMCP("VNServices")

# Weather - Open-Meteo (miễn phí)
@mcp.tool()
def weather(city: str="Hanoi, Vietnam") -> str:
    """Thời tiết hiện tại & dự báo ngắn. Trả về tiếng Việt."""
    g = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                     params={"name": city, "count": 1, "language": "vi"}).json()
    if not g.get("results"): return f"Không tìm thấy địa danh '{city}'."
    r0 = g["results"][0]
    lat, lon = r0["latitude"], r0["longitude"]
    full = f'{r0["name"]}, {r0.get("admin1","")}, {r0.get("country","")}'.strip(", ")
    w = requests.get("https://api.open-meteo.com/v1/forecast",
                     params={"latitude": lat, "longitude": lon,
                             "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                             "timezone": "Asia/Bangkok"}).json()
    cur = w["current"]
    t, hum, wind, code = cur["temperature_2m"], cur["relative_humidity_2m"], cur["wind_speed_10m"], cur["weather_code"]
    desc = {0:"Trời quang",1:"Trời quang",2:"Nhiều mây",3:"U ám",
            45:"Sương mù",48:"Sương mù",51:"Mưa phùn nhẹ",61:"Mưa nhẹ",
            63:"Mưa vừa",65:"Mưa to",71:"Tuyết rơi",80:"Mưa rào"}.get(code,"Thời tiết thay đổi")
    return f"{full}: {desc}. Nhiệt độ {t}°C, độ ẩm {hum}%, gió {wind} km/h."

# Music - iTunes Search (miễn phí)
@mcp.tool()
def music_search(query: str) -> str:
    """Tìm bài nhạc theo từ khoá tiếng Việt (iTunes)."""
    r = requests.get("https://itunes.apple.com/search",
                     params={"term": query, "country": "vn", "media": "music", "limit": 5}).json()
    if r.get("resultCount",0)==0: return "Không tìm thấy bài phù hợp."
    out = [f'- {it.get("trackName")} – {it.get("artistName")} ({it.get("collectionName","")})'
           for it in r["results"]]
    return "Gợi ý nhạc:\n" + "\n".join(out)

# News - Google News RSS (miễn phí)
@mcp.tool()
def news(topic: str="Việt Nam") -> str:
    """Tin nóng theo chủ đề (Google News)."""
    rss = f"https://news.google.com/rss/search?q={topic}&hl=vi&gl=VN&ceid=VN:vi"
    feed = feedparser.parse(rss)
    if not feed.entries: return "Không thấy bản tin phù hợp."
    return "Tin mới:\n" + "\n".join(f"- {e.title}" for e in feed.entries[:5])

# Joke - Việt hoá đơn giản
JOKES = [
    "Tại sao máy tính hay lạnh? Vì có nhiều 'quạt' (fans).",
    "Điện thoại bảo với sạc: 'Gặp cậu là mình thấy đầy năng lượng!'",
    "Học online mãi thành… cao thủ ALT+F4.",
]
@mcp.tool()
def joke() -> str:
    """Kể một câu đùa ngắn tiếng Việt."""
    return random.choice(JOKES)

if __name__ == "__main__":
    mcp.run(transport="stdio")
