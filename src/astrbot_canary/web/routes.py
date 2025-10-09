from collections.abc import Awaitable, Callable
from typing import Any
from robyn import Robyn

class AstrbotWebRoutes:
    app: Robyn | None = None
    @classmethod
    def initialize(cls, app: Robyn):
        cls.app = app
        # 类型：路径 -> 异步handler函数
        routes : dict[str, Callable[..., Awaitable[Any]]] = {}

        @app.get("/")
        async def index():
            routes["/"] = index
            return {"message": "Hello, Astrbot Canary Web!"}
        

        