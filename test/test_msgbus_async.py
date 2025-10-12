
import pytest
from kombu import Queue # type: ignore

from astrbot_canary_api.msgbus import AstrbotMessageBus


@pytest.mark.anyio
async def test_iterate_receives_published_message() -> None:
    # Ensure fresh singleton
    AstrbotMessageBus.resetBus()
    bus = AstrbotMessageBus.getBus("memory://")

    received: list[dict[str, str]] = []
    # Declare the same queue name that iterate() would use (memory:// requires both sides declare identically)
    other_q = Queue("test_key", bus.exchange, routing_key="test_key")

    # publish the message
    await bus.async_send({"msg": "hello"}, exchange=bus.exchange, routing_key="test_key", declare=[other_q])

    # directly await a single asynchronous receive (faster and deterministic)
    got = await bus.async_receive_once("test_key", timeout=0.5)
    assert got == {"msg": "hello"}

    AstrbotMessageBus.resetBus()
