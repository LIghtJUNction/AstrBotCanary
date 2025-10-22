"""原型构建阶段.

astrbot通信核心

"""

from __future__ import annotations

import asyncio
import inspect
import re
from collections.abc import Callable, Coroutine
from typing import Any, AsyncContextManager, Generic, TypeVar, get_type_hints

from astrbot_canary_api.interface import BROKER_TYPE
from pydantic import BaseModel
from yarl import URL

ResponseBody = TypeVar("ResponseBody", bound=BaseModel)


class Response(BaseModel, Generic[ResponseBody]):
    body: ResponseBody
    status_code: int = 200
    headers: dict[str, str] = {}


class Request(BaseModel):
    method: str
    path: str
    query_params: dict[str, str]
    body: BaseModel | None = None


Handler = Callable[..., Coroutine[Any, Any, Response[Any]]]
Middleware = Callable[[Handler], Handler]

F = TypeVar("F", bound=Callable[..., Any])


class AstrbotRouteMatcher:
    """路由匹配器接口
    支持路由查找,参数提取,反向查找等能力.
    """

    def __init__(self):
        # routes: (method, path) -> (handler, name)
        self.routes: list[tuple[str, str, Any, str | None]] = []

    def match(self, method: str, path: str) -> tuple[Any, dict[str, Any]] | None:
        """路由查找:根据方法和路径查找handler及参数
        返回: (handler, 参数字典) 或 None.
        """
        for m, p, handler, name in self.routes:
            if m == method:
                # 支持路径参数,如 /user/{id}
                pattern = re.sub(r"\{([^}]+)\}", r"(?P<\1>[^/]+)", p)
                match = re.match(f"^{pattern}$", path)
                if match:
                    params = match.groupdict()
                    params["route_name"] = name
                    return handler, params
        return None

    def url_for(self, name: str, **path_params: dict[str, Any]) -> str:
        """反向查找:根据路由名和参数生成完整URL."""
        for m, p, handler, n in self.routes:
            if n == name:
                # 支持路径参数替换,如 /user/{id}
                url = p
                for k, v in path_params.items():
                    url = url.replace(f"{{{k}}}", str(v))
                return url
        raise KeyError(f"No route named {name}")

    def add_route(
        self,
        method: str,
        path: str,
        handler: object,
        name: str | None = None,
    ) -> None:
        """注册路由."""
        self.routes.append((method, path, handler, name))

    def get_routes(self) -> list[tuple[str, str, Any, str | None]]:
        """获取所有路由 (方法, 路径, handler, 路由名)."""
        # 返回所有路由,包含路由名
        return [(m, p, handler, name) for m, p, handler, name in self.routes]


class AstrbotNetwork:
    """Astrbot Taskiq Network: 仿FastAPI风格的taskiq封装
    负责路由分发,中间件管理,异常处理.
    """

    scheme: str = "astrbot"
    broker: BROKER_TYPE
    routes: dict[tuple[str, str], Any]
    sub_routers: dict[str, AstrbotNetwork]
    middlewares: list[Middleware]

    def __init__(
        self,
        broker: BROKER_TYPE,
        prefix: str = "",
        lifespan: AsyncContextManager[Any] | None = None,
    ):
        self.broker = broker
        self.routes = {}
        self.sub_routers = {}
        self.middlewares = []
        if prefix:
            self.prefix = (URL("/") / prefix.strip("/")).path
        else:
            self.prefix = "/"
        self.matcher = AstrbotRouteMatcher()

    def add_middleware(self, middleware: Middleware) -> None:
        """添加中间件."""
        self.middlewares.append(middleware)

    def add_router(self, router: AstrbotNetwork) -> None:
        """添加子路由器."""
        self.sub_routers[router.prefix] = router
        # 合并 matcher 路由
        for methods, path, handler in router.get_routes():
            for method in methods:
                if path:
                    full_path = f"{router.prefix.rstrip('/')}/{path.lstrip('/')}"
                else:
                    full_path = router.prefix
                self.matcher.add_route(method, full_path, handler)

    def get_routes(self) -> list[tuple[list[str], str, Any]]:
        routes: list[tuple[list[str], str, Any]] = []
        for (method, path), handler in self.routes.items():
            routes.append(([method], path, handler))
        for prefix, router in self.sub_routers.items():
            sub_routes = router.get_routes()
            for methods, sub_path, handler in sub_routes:
                if sub_path:
                    full_path = f"{prefix.rstrip('/')}/{sub_path.lstrip('/')}"
                else:
                    full_path = prefix
                routes.append((methods, full_path, handler))
        return routes

    def get(
        self,
        path: str,
        **kwargs: object,
    ) -> Callable[[F], F]:
        """路径(用于生成任务名,示例:/echo )+标签."""

        def decorator(func: F) -> F:
            url = URL(path)
            norm_path = url.path

            rel = norm_path.lstrip("/")
            # build URL using yarl's chainable API:
            # start with scheme, then append relative path
            base_url = URL().with_scheme(self.scheme)
            if rel:
                url = base_url / rel
                norm_path = url.path
            else:
                url = base_url
                norm_path = "/"

            self.routes[("GET", norm_path)] = func
            # 注册到 matcher
            full_path = f"{self.prefix.rstrip('/')}/{norm_path.lstrip('/')}"
            self.matcher.add_route("GET", full_path, func)
            return func

        return decorator

    def post(self, path: str):
        """POST请求装饰器."""

    def put(self, path: str):
        """PUT请求装饰器."""

    def delete(self, path: str):
        """DELETE请求装饰器."""

    def head(self, path: str):
        """HEAD请求装饰器."""

    def options(self, path: str):
        """OPTIONS请求装饰器."""

    def patch(self, path: str):
        """PATCH请求装饰器."""

    def api_route(self, path: str, methods: list[str]) -> object:
        """通用路由装饰器,接受所有HTTP方法."""


class AstrbotRequests:
    """请求封装."""

    _network: AstrbotNetwork | None = None

    @classmethod
    def set_network(cls, network: AstrbotNetwork) -> None:
        cls._network = network

    @classmethod
    def get(cls, path: str | URL) -> object:
        """发送GET请求,模拟调用路由.network 通过 set_network 共享.."""
        return cls._send_request("GET", path)

    @classmethod
    def post(cls, path: str | URL, body: BaseModel | None = None) -> object:
        """发送POST请求,模拟调用路由.network 通过 set_network 共享.."""
        return cls._send_request("POST", path, body)

    @classmethod
    def _send_request(
        cls,
        method: str,
        path: str | URL,
        body: BaseModel | None = None,
    ) -> object:
        if cls._network is None:
            msg = ("AstrbotRequests network not set. Call set_network first.",)
            raise RuntimeError(msg)

        if isinstance(path, str):
            url = URL(path)
            norm_path = url.path
            rel = norm_path.lstrip("/")
            query_params = dict(url.query)
            url = URL("/") / rel if rel else URL("/")
        else:
            url = path
            query_params = {}
        norm_path = url.path
        if not norm_path.startswith("/"):
            norm_path = "/" + norm_path
        handler_info = cls._network.matcher.match(method, norm_path)
        if handler_info:
            handler: Handler = handler_info[0]
            params = handler_info[1]
            # 获取 handler 参数类型
            sig = inspect.signature(handler)
            param_types = get_type_hints(handler)
            args: list[Any] = []
            for param_name in sig.parameters:
                if param_name in param_types:
                    param_type = param_types[param_name]
                    if param_type == Request:
                        args.append(
                            Request(
                                method=method,
                                path=norm_path,
                                query_params=query_params,
                                body=body,
                            ),
                        )
                    elif issubclass(param_type, BaseModel):
                        # 创建模型实例
                        model_data = {
                            k: v
                            for k, v in params.items()
                            if k in param_type.model_fields
                        }
                        args.append(param_type(**model_data))
                    else:
                        args.append(params.get(param_name))
                else:
                    args.append(params.get(param_name))
            for middleware in reversed(cls._network.middlewares):
                handler = middleware(handler)
            try:
                result = asyncio.run(handler(*args))
            except RuntimeError:
                return None
            else:
                return result.body
        else:
            return None
