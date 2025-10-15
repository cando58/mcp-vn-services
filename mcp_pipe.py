# mcp_pipe.py
# Usage: python mcp_pipe.py vn_services.py
import os, sys, json, threading, subprocess, time
import websocket

ENDPOINT = os.environ.get("MCP_ENDPOINT", "").strip()
if not ENDPOINT:
    print("ERROR: Missing MCP_ENDPOINT env.", file=sys.stderr)
    sys.exit(2)

if len(sys.argv) < 2:
    print("Usage: python mcp_pipe.py <tool_script.py>", file=sys.stderr)
    sys.exit(2)

tool_script = sys.argv[1]

# spawn tool (stdio MCP server)
proc = subprocess.Popen(
    [sys.executable, tool_script],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
)

def pump_stderr():
    for line in proc.stderr:
        sys.stderr.write(line)
threading.Thread(target=pump_stderr, daemon=True).start()

ws = None
ws_lock = threading.Lock()

def on_open(_ws):
    print("MCP_PIPE: Connected to endpoint.", file=sys.stderr)

def on_close(_ws, *_):
    print("MCP_PIPE: Disconnected. Reconnecting...", file=sys.stderr)

def on_error(_ws, err):
    print(f"MCP_PIPE: WS error: {err}", file=sys.stderr)

def on_message(_ws, message):
    # inbound -> child stdin
    try:
        proc.stdin.write(message + "\n")
        proc.stdin.flush()
    except Exception as e:
        print(f"MCP_PIPE: write to child failed: {e}", file=sys.stderr)

def child_out_loop():
    # child stdout -> outbound
    for line in proc.stdout:
        line = line.rstrip("\n")
        if not line:
            continue
        with ws_lock:
            try:
                if ws and ws.sock and ws.sock.connected:
                    ws.send(line)
            except Exception as e:
                print(f"MCP_PIPE: send failed: {e}", file=sys.stderr)

threading.Thread(target=child_out_loop, daemon=True).start()

def run_forever():
    global ws
    while True:
        try:
            ws = websocket.WebSocketApp(
                ENDPOINT,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
            )
            ws.run_forever(ping_interval=20, ping_timeout=10)
        except Exception as e:
            print(f"MCP_PIPE: run_forever error: {e}", file=sys.stderr)
        time.sleep(3)

if __name__ == "__main__":
    run_forever()
