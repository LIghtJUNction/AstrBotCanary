"""Simple standalone demo that sends and receives a message using AstrbotMessageBus.
Run with: & .\\.venv\\Scripts\\python.exe .\test\run_msgbus_demo.py
"""
import anyio
from kombu import Queue # type: ignore

from astrbot_canary_api.msgbus import AstrbotMessageBus


async def main() -> None:
    try:
        AstrbotMessageBus.resetBus()
        bus = AstrbotMessageBus.getBus("memory://astrbot")

        q = Queue("demo_test", bus.exchange, routing_key="demo_test")

        print("[demo] sending...")
        await bus.async_send({"msg": "hello demo"}, exchange=bus.exchange, routing_key="demo_test", declare=[q])

        print("[demo] receiving (timeout=2s)...")
        got = await bus.async_receive_once("demo_test", timeout=2.0)
        print("[demo] received:", got)

    except Exception as e:
        print("[demo] error:", type(e).__name__, e)
    finally:
        AstrbotMessageBus.resetBus()


if __name__ == "__main__":
    anyio.run(main)
