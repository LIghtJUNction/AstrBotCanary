from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from pydantic import BaseModel
from robyn import Robyn


class AuthData(BaseModel):
    token: str
    username: str
    change_pwd_hint: str | None = None



class AstrbotWebRoutes:
    app: Robyn | None = None
    routes : dict[str, Callable[..., Awaitable[Any]]] = {}
    @classmethod
    def initialize(cls, app: Robyn , frontend: Path):
        cls.app = app
        cls.app.serve_directory("/", str(frontend), index_file="index.html" , show_files_listing=True)

        # @cls.app.before_request()
        

        # @cls.app.after_request()


        @app.get("/api")
        async def index():
            cls.routes["/api"] = index
            return {"message": "Hello, Astrbot Canary Web!"}
        