from mcp.server.fastmcp import FastMCP
import os, requests, feedparser
from tools import storage

mcp = FastMCP("VN Tools")

OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

@mcp.tool()
def weather(city: str) -> dict:
    """Get current weather in Vietnamese (metric, °C). Requires OPENWEATHER_KEY."""
    if not OPENWEATHER_KEY:
        return {"success": False, "error": "Missing OPENWEATHER_KEY env"}
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": OPENWEATHER_KEY, "units": "metric", "lang": "vi"}
    r = requests.get(url, params=params, timeout=10)
    try:
        data = r.json()
    except Exception:
        return {"success": False, "error": "Invalid weather response"}
    if r.status_code != 200:
        return {"success": False, "error": data.get("message", "weather api error")}
    out = {
        "city": data.get("name"),
        "temp_c": data["main"]["temp"],
        "feels_like_c": data["main"]["feels_like"],
        "humidity": data["main"]["humidity"],
        "description": (data["weather"][0]["description"] if data.get("weather") else ""),
        "wind_mps": data["wind"]["speed"],
    }
    return {"success": True, "result": out}

@mcp.tool()
def music_search(query: str, limit: int = 5) -> dict:
    """Search songs using iTunes Search API (no key). Returns list of tracks with preview links."""
    import urllib.parse
    q = urllib.parse.quote_plus(query)
    url = f"https://itunes.apple.com/search?term={q}&entity=song&limit={max(1, min(limit, 25))}"
    r = requests.get(url, timeout=10)
    js = r.json()
    tracks = []
    for it in js.get("results", []):
        tracks.append({
            "track": it.get("trackName"),
            "artist": it.get("artistName"),
            "album": it.get("collectionName"),
            "previewUrl": it.get("previewUrl"),
            "trackViewUrl": it.get("trackViewUrl"),
        })
    return {"success": True, "result": tracks}

@mcp.tool()
def news(query: str = "", country: str = "vn", limit: int = 5) -> dict:
    """Get news. Uses NEWS_API_KEY if set, else Google News RSS (VI)."""
    limit = max(1, min(limit, 20))
    if NEWS_API_KEY:
        base = "https://newsapi.org/v2/"
        if query:
            url = base + "everything"
            params = {"q": query, "pageSize": limit, "language": "vi", "apiKey": NEWS_API_KEY, "sortBy": "publishedAt"}
        else:
            url = base + "top-headlines"
            params = {"country": country, "pageSize": limit, "apiKey": NEWS_API_KEY}
        r = requests.get(url, params=params, timeout=10)
        js = r.json()
        if r.status_code != 200:
            return {"success": False, "error": js.get("message", "news api error")}
        arts = []
        for a in js.get("articles", []):
            arts.append({"title": a.get("title"), "url": a.get("url"), "source": a.get("source", {}).get("name")})
        return {"success": True, "result": arts}
    else:
        # Google News RSS (Vietnamese)
        feed_url = "https://news.google.com/rss?hl=vi&gl=VN&ceid=VN:vi"
        d = feedparser.parse(feed_url)
        items = []
        for e in d.entries[:limit]:
            items.append({"title": e.title, "url": e.link, "source": "Google News"})
        return {"success": True, "result": items}

@mcp.tool()
def joke(category: str = "Any") -> dict:
    """Return a random joke (English) from JokeAPI."""
    import urllib.parse
    cat = urllib.parse.quote(category or "Any")
    url = f"https://v2.jokeapi.dev/joke/{cat}?type=single&safe-mode"
    r = requests.get(url, timeout=10)
    js = r.json()
    if js.get("error"):
        return {"success": False, "error": js.get("message", "joke api error")}
    return {"success": True, "result": js.get("joke")}

@mcp.tool()
def alarm_set(iso_time: str, title: str) -> dict:
    """Create an alarm saved in /data/alarms.json. Example iso_time: 2025-10-01T07:30:00+07:00"""
    a = storage.add_alarm(iso_time, title)
    return {"success": True, "result": a}

@mcp.tool()
def alarm_list() -> dict:
    """List all alarms."""
    return {"success": True, "result": storage.list_alarms()}

@mcp.tool()
def alarm_delete(alarm_id: str) -> dict:
    """Delete alarm by id."""
    return {"success": True, "result": storage.delete_alarm(alarm_id)}

if __name__ == "__main__":
    # Run as stdio transport for XiaoZhi MCP pipe
    mcp.run(transport="stdio")
