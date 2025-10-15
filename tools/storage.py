import json, os, uuid

DATA_DIR = os.environ.get("DATA_DIR", "/data")
ALARM_FILE = os.path.join(DATA_DIR, "alarms.json")
os.makedirs(DATA_DIR, exist_ok=True)

def _load():
    if not os.path.exists(ALARM_FILE):
        return {"alarms": []}
    with open(ALARM_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {"alarms": []}

def _save(data):
    with open(ALARM_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_alarm(iso_time: str, title: str):
    data = _load()
    alarm = {"id": str(uuid.uuid4()), "time": iso_time, "title": title}
    data["alarms"].append(alarm)
    _save(data)
    return alarm

def list_alarms():
    return _load().get("alarms", [])

def delete_alarm(alarm_id: str):
    data = _load()
    before = len(data["alarms"])
    data["alarms"] = [a for a in data["alarms"] if a["id"] != alarm_id]
    _save(data)
    return {"deleted": before - len(data["alarms"])}
