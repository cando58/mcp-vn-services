
import asyncio, os, sys, signal, subprocess, logging
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s - MCP_PIPE - %(levelname)s - %(message)s")
MCP_ENDPOINT = os.getenv("MCP_ENDPOINT")
PING_INTERVAL = int(os.getenv("MCP_PING_INTERVAL", "20"))  # seconds

if not MCP_ENDPOINT:
    logging.error("Missing MCP_ENDPOINT env.")
    sys.exit(1)

async def pipe_stdio(ws, proc):
    async def ws_to_stdin():
        try:
            async for msg in ws:
                if isinstance(msg, bytes):
                    proc.stdin.write(msg)
                    await proc.stdin.drain()
                elif isinstance(msg, str):
                    # XiaoZhi uses binary frames; ignore text frames
                    pass
        except Exception as e:
            logging.warning(f"ws_to_stdin ended: {e}")

    async def stdout_to_ws():
        try:
            while True:
                data = await proc.stdout.read(4096)
                if not data:
                    break
                await ws.send(data)
        except Exception as e:
            logging.warning(f"stdout_to_ws ended: {e}")

    async def ping_task():
        try:
            while True:
                await asyncio.sleep(PING_INTERVAL)
                try:
                    await ws.ping()
                except Exception as e:
                    logging.warning(f"Ping failed: {e}")
                    break
        except asyncio.CancelledError:
            pass

    t1 = asyncio.create_task(ws_to_stdin())
    t2 = asyncio.create_task(stdout_to_ws())
    t3 = asyncio.create_task(ping_task())
    await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
    for t in (t1, t2, t3):
        t.cancel()

async def main():
    logging.info("Connecting to endpoint...")
    async for ws in websockets.connect(MCP_ENDPOINT, max_size=10*1024*1024):  # auto-reconnect
        logging.info("Connected to endpoint.")
        # Launch the MCP server process (server.py received as argv[1])
        cmd = [sys.executable, sys.argv[1]] + sys.argv[2:]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            await pipe_stdio(ws, proc)
        finally:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
            await proc.wait()
            logging.info("Disconnected, will reconnect...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
