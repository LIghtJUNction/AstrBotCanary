from __future__ import annotations

from collections.abc import Awaitable, Callable
from types import CoroutineType
from taskiq import AsyncTaskiqDecoratedTask, InMemoryBroker
from yarl import URL
from astrbot_canary_api.interface import BROKER_TYPE
from typing import Any, AsyncContextManager

class Response:
    def __init__(self, body: Any) -> None:
        self.body: Any = body


class AstrbotRouteMatcher():
    """
    路由匹配器接口
    支持路由查找、参数提取、反向查找等能力
    """
    def __init__(self):
        # routes: (method, path) -> (handler, name)
        self.routes: list[tuple[str, str, Any, str | None]] = []

    def match(self, method: str, path: str) -> tuple[Any, dict[str, Any]] | None:
        """
        路由查找：根据方法和路径查找handler及参数
        返回: (handler, 路径参数字典) 或 None
        """
        # 简单实现：精确匹配
        for m, p, handler, name in self.routes:
            if m == method and p == path:
                # 这里可以返回 name 作为参数之一，便于后续扩展
                return handler, {"route_name": name}
        return None

    def url_for(self, name: str, **path_params: dict[str, Any]) -> str:
        """
        反向查找：根据路由名和参数生成完整URL
        """
        for m, p, handler, n in self.routes:
            if n == name:
                # 支持路径参数替换，如 /user/{id}
                url = p
                for k, v in path_params.items():
                    url = url.replace(f"{{{k}}}", str(v))
                return url
        raise KeyError(f"No route named {name}")

    def add_route(self, method: str, path: str, handler: Any, name: str | None = None) -> None:
        """
        注册路由
        """
        self.routes.append((method, path, handler, name))

    def get_routes(self) -> list[tuple[str, str, Any, str | None]]:
        """
        获取所有路由 (方法, 路径, handler, 路由名)
        """
        # 返回所有路由，包含路由名
        return [(m, p, handler, name) for m, p, handler, name in self.routes]




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
            prefix: str = "",
            lifespan: AsyncContextManager[Any] | None = None,
        ):
        self.broker = broker
        self.routes = {}
        self.sub_routers = {}
        self.prefix = str(URL(prefix).with_path(f"/{prefix.strip('/')}/") if prefix else URL("/"))
        self.matcher = AstrbotRouteMatcher()
    
    def add_router(self, router: AstrbotNetwork) -> None:
        """添加子路由器"""
        self.sub_routers[router.prefix] = router
        # 合并 matcher 路由
        for methods, path, handler in router.get_routes():
            for method in methods:
                self.matcher.add_route(method, path, handler)

    def get_routes(self) -> list[tuple[list[str], str, Any]]:
        routes: list[tuple[list[str], str, Any]] = []
        for (method, path), handler in self.routes.items():
            if path:
                full_path = str(URL(self.prefix) / path.strip("/"))
            else:
                full_path = self.prefix
            routes.append(([method], full_path, handler))
        for prefix, router in self.sub_routers.items():
            sub_routes = router.get_routes()
            for methods, sub_path, handler in sub_routes:
                if sub_path:
                    full_path = str(URL(prefix) / sub_path.strip("/"))
                else:
                    full_path = prefix
                routes.append((methods, full_path, handler))
        return routes

    def get(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Awaitable[Any]]], Any]:
        def decorator(func: Callable[..., Awaitable[Any]]) -> AsyncTaskiqDecoratedTask[Any, CoroutineType[Any, Any, Response]]:
            norm_path = str(URL(path).with_path(f"/{path.strip('/')}/"))
            task_name = f"{self.scheme}://{norm_path}"
            @self.broker.task(task_name=task_name, **kwargs)
            async def wrapper(*args: Any, **kwargs: Any) -> Response:
                result = await func(*args, **kwargs)
                return Response(result)
            for k, v in kwargs.items():
                setattr(wrapper, k, v)
            self.routes[("GET", norm_path)] = wrapper
            # 注册到 matcher
            full_path = str(URL(self.prefix) / path.strip("/"))
            self.matcher.add_route("GET", full_path, wrapper)
            return wrapper
        return decorator
    
    def post(self, path: str):
        """POST请求装饰器"""
        ...

    def put(self, path: str):
        """PUT请求装饰器"""
        ...
    
    def delete(self, path: str):
        """DELETE请求装饰器"""
        ...

    def head(self, path: str):
        """HEAD请求装饰器"""
        ...

    def options(self, path: str):
        """OPTIONS请求装饰器"""
        ...

    def patch(self, path: str):
        """PATCH请求装饰器"""
        ...

    def api_route(self, path: str, methods: list[str]) -> Any:
        """通用路由装饰器，接受所有HTTP方法"""
        ...



class AstrbotRequests:
    """ 请求封装 """
    _network: AstrbotNetwork | None = None

    @classmethod
    def set_network(cls, network: AstrbotNetwork) -> None:
        cls._network = network

    @classmethod
    def get(cls, path: str | URL) -> Any:
        """发送GET请求，模拟调用路由。network 通过 set_network 共享。"""
        if cls._network is None:
            raise RuntimeError("AstrbotRequests network not set. Call set_network first.")
        if isinstance(path, URL):
            path_str = path.path.lstrip("/")
        else:
            path_str = str(path).lstrip("/")
        url = URL().with_scheme("astrbot") / path_str
        print(f"Sending GET request to {url}")
        # 查找路径统一以 / 开头
        full_path = "/" + path_str.lstrip("/")
        handler_info = cls._network.matcher.match("GET", full_path)
        if handler_info:
            handler, _ = handler_info
            import asyncio
            result = asyncio.run(handler())
            print(f"Response: {result.body}")
            return result.body
        else:
            print("404 Not Found")
            return None




if __name__ == "__main__":
    broker = InMemoryBroker()
    root_network = AstrbotNetwork(broker=broker)

    sub_network = AstrbotNetwork(broker=broker, prefix="/api")

    @root_network.get("/hello")
    async def hello_handler() -> str:
        return "Hello, Astrbot!"
    
    @sub_network.get("/status")
    async def status_handler() -> str:
        return "Status: OK"
    
    sub_sub_network = AstrbotNetwork(broker=broker, prefix="/v1")
    @sub_sub_network.get("/info")
    async def info_handler() -> str:
        return "Info: Astrbot Canary v1.0"
    
    sub_network.add_router(sub_sub_network)

    root_network.add_router(sub_network)

    AstrbotRequests.set_network(root_network)
    AstrbotRequests.get("/api/status")

    AstrbotRequests.get("/api/v1/info")
