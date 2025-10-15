# vn_services.py
# MCP tools: thời tiết, nhạc, tin tức, câu đùa, báo thức
from mcp.server.fastmcp import FastMCP
import requests, feedparser, random, os, json, threading, uuid, re
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateparser, tz as tzmod

mcp = FastMCP("VNServices")

# ---------- Helpers ----------
def _tz(tzname: str):
    z = tzmod.gettz(tzname or "Asia/Ho_Chi_Minh")
    return z or tzmod.gettz("Asia/Ho_Chi_Minh")

# Simple file/redis KV for alarms
class AlarmStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.file = os.environ.get("ALARM_FILE", "/data/alarms.json")
        self._ensure_dir()
        self.redis_url = os.environ.get("UPSTASH_REDIS_URL") or ""
        self._redis = None
        if self.redis_url:
            try:
                import redis
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
            except Exception:
                self._redis = None

    def _ensure_dir(self):
        try:
            os.makedirs(os.path.dirname(self.file), exist_ok=True)
        except Exception:
            pass

    def _load_file(self):
        if not os.path.exists(self.file):
            return []
        try:
            with open(self.file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_file(self, data):
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _get(self):
        if self._redis:
            raw = self._redis.get("alarms_json") or "[]"
            try: return json.loads(raw)
            except Exception: return []
        return self._load_file()

    def _set(self, data):
        if self._redis:
            self._redis.set("alarms_json", json.dumps(data, ensure_ascii=False))
        else:
            self._save_file(data)

    def add(self, alarm):
        with self.lock:
            arr = self._get()
            arr.append(alarm)
            self._set(arr)

    def list(self):
        with self.lock:
            return self._get()

    def delete(self, alarm_id):
        with self.lock:
            arr = self._get()
            n = len(arr)
            arr = [a for a in arr if a.get("id") != alarm_id]
            self._set(arr)
            return n - len(arr)

    def pop_due(self, ts_utc_until):
        """pop alarms with ts_utc <= given time"""
        with self.lock:
            arr = self._get()
            due, keep = [], []
            for a in arr:
                if a.get("ts_utc", 0) <= ts_utc_until:
                    due.append(a)
                else:
                    keep.append(a)
            self._set(keep)
            return due

AL = AlarmStore()

def _pretty_local(ts_utc: int, tzname: str):
    dt = datetime.fromtimestamp(ts_utc, tz=timezone.utc).astimezone(_tz(tzname))
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")

def _parse_when(when: str, tzname: str):
    when = (when or "").strip().lower()
    zone = _tz(tzname)
    now = datetime.now(zone)

    # relative forms: "in 10 minutes", "in 2 hours", "trong 15 phút", "sau 1 giờ"
    m = re.match(r"(in|trong|sau)\s+(\d+)\s+(minute|min|phút|hour|giờ|day|ngày)s?", when)
    if m:
        n = int(m.group(2))
        unit = m.group(3)
        delta = timedelta(minutes=n) if unit in ("minute", "min", "phút") else \
                timedelta(hours=n) if unit in ("hour", "giờ") else \
                timedelta(days=n)
        target = now + delta
        return target

    # absolute (ngày/giờ): để dateutil parse, default=now cho phần thiếu
    try:
        dt = dateparser.parse(when, dayfirst=True, default=now)
        if dt.tzinfo is None:
            dt = zone.localize(dt) if hasattr(zone, "localize") else dt.replace(tzinfo=zone)
        return dt.astimezone(zone)
    except Exception:
        return None

# ---------- Tools: Weather ----------
@mcp.tool()
def weather(city: str="Hanoi, Vietnam") -> str:
    """Thời tiết hiện tại & dự báo ngắn (Open-Meteo). Trả về tiếng Việt."""
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

# ---------- Tools: Music ----------
@mcp.tool()
def music_search(query: str) -> str:
    """Tìm bài nhạc theo từ khoá tiếng Việt (iTunes)."""
    r = requests.get("https://itunes.apple.com/search",
                     params={"term": query, "country": "vn", "media": "music", "limit": 5}).json()
    if r.get("resultCount",0)==0: return "Không tìm thấy bài phù hợp."
    out = [f'- {it.get("trackName")} – {it.get("artistName")} ({it.get("collectionName","")})'
           for it in r["results"]]
    return "Gợi ý nhạc:\n" + "\n".join(out)

# ---------- Tools: News ----------
@mcp.tool()
def news(topic: str="Việt Nam") -> str:
    """Tin nóng theo chủ đề (Google News)."""
    rss = f"https://news.google.com/rss/search?q={topic}&hl=vi&gl=VN&ceid=VN:vi"
    feed = feedparser.parse(rss)
    if not feed.entries: return "Không thấy bản tin phù hợp."
    return "Tin mới:\n" + "\n".join(f"- {e.title}" for e in feed.entries[:5])

# ---------- Tools: Joke ----------
JOKES = [
    "Tại sao máy tính hay lạnh? Vì có nhiều 'quạt' (fans).",
    "Điện thoại bảo với sạc: 'Gặp cậu là mình thấy đầy năng lượng!'",
    "Học online mãi thành… cao thủ ALT+F4.",
]
@mcp.tool()
def joke() -> str:
    """Kể một câu đùa ngắn tiếng Việt."""
    return random.choice(JOKES)

# ---------- Tools: Alarm ----------
@mcp.tool()
def set_alarm(when: str, tz: str="Asia/Ho_Chi_Minh", label: str="") -> dict:
    """
    Tạo báo thức.
    - when: ví dụ '07:30 16/10/2025', 'in 10 minutes', 'trong 2 giờ'
    - tz: IANA timezone, mặc định Asia/Ho_Chi_Minh
    - label: nhãn
    Trả về: {id, time_local, time_utc, label}
    """
    dt_local = _parse_when(when, tz)
    if not dt_local:
        return {"success": False, "error": "Không hiểu thời điểm. Ví dụ: '07:30 16/10/2025' hoặc 'in 10 minutes'."}
    ts_utc = int(dt_local.astimezone(timezone.utc).timestamp())
    aid = uuid.uuid4().hex[:10]
    item = {"id": aid, "tz": tz, "label": label or "", "ts_utc": ts_utc}
    AL.add(item)
    return {"success": True, "id": aid,
            "time_local": _pretty_local(ts_utc, tz),
            "time_utc": datetime.fromtimestamp(ts_utc, tz=timezone.utc).isoformat()}

@mcp.tool()
def list_alarms(tz: str="Asia/Ho_Chi_Minh") -> str:
    """Liệt kê báo thức đã đặt (theo giờ địa phương tz)."""
    arr = sorted(AL.list(), key=lambda a: a.get("ts_utc", 0))
    if not arr: return "Chưa có báo thức nào."
    lines = [f'- [{a["id"]}] {_pretty_local(a["ts_utc"], tz)} — {a.get("label","")}'.rstrip(" — ")
             for a in arr]
    return "Danh sách báo thức:\n" + "\n".join(lines)

@mcp.tool()
def delete_alarm(alarm_id: str) -> str:
    """Xoá 1 báo thức theo id (xem list_alarms)."""
    n = AL.delete(alarm_id.strip())
    return "Đã xoá." if n>0 else "Không tìm thấy id cần xoá."

@mcp.tool()
def due_alarms(tz: str="Asia/Ho_Chi_Minh", within_minutes: int=1) -> str:
    """
    Trả về & đồng thời gỡ những báo thức đã đến hạn (<= now + within_minutes).
    Dùng cho thiết bị thỉnh thoảng gọi kiểm tra để phát chuông.
    """
    now_utc = datetime.now(timezone.utc).timestamp()
    horizon = int(now_utc + within_minutes*60)
    due = AL.pop_due(horizon)
    if not due: return "No due alarms."
    lines = [f'- [{a["id"]}] {_pretty_local(a["ts_utc"], tz)} — {a.get("label","")}'.rstrip(" — ")
             for a in due]
    return "Due alarms:\n" + "\n".join(lines)

if __name__ == "__main__":
    mcp.run(transport="stdio")
