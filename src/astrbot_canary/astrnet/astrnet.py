from collections.abc import Awaitable, Callable
from types import CoroutineType
from taskiq import AsyncTaskiqDecoratedTask

from astrbot_canary_api.interface import BROKER_TYPE
from typing import Any, AsyncContextManager

class Response:
    def __init__(self, body: Any) -> None:
        self.body: Any = body

class AstrbotNetwork():
    """ Astrbot Taskiq Network: 仿FastAPI风格的taskiq封装
    负责路由分发、中间件管理、异常处理
    """
    scheme: str = "astrbot"
    broker: BROKER_TYPE
    routes: dict[tuple[str, str], Any]
    sub_routers: dict[str, 'AstrbotNetwork']

    def __init__(
            self,
            broker: BROKER_TYPE,
            lifespan: AsyncContextManager[Any] | None = None,
        ):
        self.broker = broker
        self.routes = {}
        self.sub_routers = {}
    
    def normalize_path(self, path: str) -> str:
        """规范化路径，去除最后的斜杠，根路径变成空字符串，并去掉前导斜杠"""
        p = path
        if p.endswith("/"):
            p = p[:-1]
        if p.startswith("/"):
            p = p[1:]
        return p

    def get(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Awaitable[Any]]], Any]:
        """注册 GET 路由
        path: 任务路径
        kwargs: 任务标签
        """
        def decorator(func: Callable[..., Awaitable[Any]]) -> AsyncTaskiqDecoratedTask[Any, CoroutineType[Any, Any, Response]]:
            norm_path = self.normalize_path(path)
            task_name = f"{self.scheme}://{norm_path}"
            @self.broker.task(task_name=task_name, **kwargs)
            async def wrapper(*args: Any, **kwargs: Any) -> Response:
                result = await func(*args, **kwargs)
                return Response(result)
            # 挂载所有标签属性到任务对象
            for k, v in kwargs.items():
                setattr(wrapper, k, v)
            self.routes[("GET", norm_path)] = wrapper
            return wrapper
        return decorator
    
    
    