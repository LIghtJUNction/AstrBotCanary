import pytest
from taskiq import InMemoryBroker
from astrbot_canary.astrnet.astrnet import AstrbotNetwork


@pytest.fixture
def astrnet():
    broker = InMemoryBroker()
    return AstrbotNetwork(broker=broker)
def test_echo_route_registration(astrnet):
    # 注册路由
    @astrnet.get("/echo", tag1="a", tag2="b")
    async def echo(msg: str) -> str:
        return msg

    # 检查路由是否注册成功
    route_key = ("GET", "echo")
    assert route_key in astrnet.routes

    # 检查任务名和标签
    task = astrnet.routes[route_key]
    assert getattr(task, "task_name", None) == "astrbot://echo"
    assert getattr(task, "tag1", None) == "a"
    assert getattr(task, "tag2", None) == "b"

@pytest.mark.asyncio
async def test_echo_route_call(astrnet):
    @astrnet.get("/echo")
    async def echo(msg: str) -> str:
        return msg

    # 获取注册的任务
    route_key = ("GET", "echo")
    task = astrnet.routes[route_key]

    # 直接调用 wrapper（模拟 Taskiq 执行）
    result = await task("hello")
    # Response(result) 包裹，假设 Response 有 .body 属性
    assert hasattr(result, "body")
    assert result.body == "hello"