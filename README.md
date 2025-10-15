# MCP VN Tools (Weather, Music, News, Jokes, Alarms)

A ready-to-deploy **MCP server** for XiaoZhi AI, running on **Railway** (or any container platform).
Includes tools:
- `weather(city)` — OpenWeather (metric, °C)
- `music_search(query, limit)` — iTunes Search (no API key required)
- `news(query, country, limit)` — NewsAPI (if `NEWS_API_KEY`) or Google News RSS fallback
- `joke(category)` — JokeAPI (English)
- `alarm_set(iso_time, title)` / `alarm_list()` / `alarm_delete(id)` — simple alarms stored in JSON

## 1) Deploy to Railway

1. Fork this repo to your GitHub.
2. On Railway: **New Project → Deploy from GitHub Repo** (select your fork).
3. In Railway → **Variables**, add:
   - `MCP_ENDPOINT` = your XiaoZhi **MCP endpoint** (from *Agent → MCP Settings → Get MCP Endpoint*). Must start with `wss://...`.
   - `OPENWEATHER_KEY` = your free key from https://openweathermap.org/ (required for weather)
   - *(optional)* `NEWS_API_KEY` = your NewsAPI key (https://newsapi.org/). If omitted, will use Google News RSS fallback.
4. Deploy. Railway will run `mcp_pipe.py` which connects to XiaoZhi and starts `server.py`.

> Notes
> - Files are stored under `/data` inside the container. This storage is ephemeral (resets on redeploy).

## 2) Connect in XiaoZhi

- In your Agent (console.xiaozhi.me) → **MCP Settings**:
  - Official Services: add ones you want (e.g., Weather, Music, Knowledge base)
  - Custom Services: click **Get MCP Endpoint** → copy the `wss://...token=...` URL.
- Paste this endpoint into Railway `MCP_ENDPOINT` variable.
- **Save** in XiaoZhi, then **reboot** the device.

## 3) Tools Overview

### weather(city: str) -> dict
Returns current weather for the city (metric), using OpenWeather.

### music_search(query: str, limit: int = 5) -> list
Returns top songs from iTunes Search.

### news(query: str = "", country: str = "vn", limit: int = 5) -> list
- If `NEWS_API_KEY` provided → uses NewsAPI.
- Else → falls back to Google News RSS (VI).

### joke(category: str = "Any") -> dict
Returns a random joke from JokeAPI (English).

### alarm_set(iso_time: str, title: str) -> dict
Stores an alarm into `/data/alarms.json`. `iso_time` is an ISO8601 string (e.g. `2025-10-01T07:30:00+07:00`).

### alarm_list() -> list
List all alarms.

### alarm_delete(id: str) -> dict
Delete alarm by its id.

## 4) Local run (optional)

```bash
pip install -r requirements.txt
# The MCP server itself runs over stdio; to test locally, you need a MCP client.
# On Railway it is launched by mcp_pipe.py automatically.
```

## 5) Security
- **Never** share your MCP endpoint publicly. Regenerate token in XiaoZhi if leaked.
- Keep API keys in **Railway Variables**, not in code.
