from dependency_injector.containers import Container
from dependency_injector.providers import Provider

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from astrbot_canary_web.models import Base, Response
from astrbot_canary_api import IAstrbotConfig, IAstrbotConfigEntry
from astrbot_canary_api.enums import AstrBotModuleType
from logging import getLogger , Logger

from astrbot_canary_api.interface import IAstrbotDatabase, IAstrbotPaths
from astrbot_canary_api.types import BROKER_TYPE
from astrbot_canary_web.config import AstrbotCanaryWebConfig
from astrbot_canary_web.frontend import AstrbotCanaryFrontend

from astrbot_canary_web.api import api_router

logger: Logger = getLogger("astrbot_canary.module.web")
class AstrbotCanaryWeb():
    name = "canary_web"
    pypi_name = "astrbot_canary_web"
    module_type = AstrBotModuleType.WEB
    version = "0.1.0"
    authors = ["LIghtJUNction"]
    description = "Web UI module for Astrbot Canary."
    enabled = True

    def Awake(self,deps: Container) -> None:
        logger.info(f"{self.name} v{self.version} is awakening.")
        self.deps = deps
        paths_provider: Provider[type[IAstrbotPaths]] = deps.AstrbotPaths
        config_provider: Provider[type[IAstrbotConfig]] = deps.AstrbotConfig
        cfg_entry_provider: Provider[type[IAstrbotConfigEntry]] = deps.AstrbotConfigEntry
        db_provider: Provider[type[IAstrbotDatabase]] = deps.AstrbotDatabase
        BROKER: Provider[BROKER_TYPE] = deps.BROKER
        paths_cls: type[IAstrbotPaths] = paths_provider()
        config_cls: type[IAstrbotConfig] = config_provider()
        cfg_entry_cls: type[IAstrbotConfigEntry] = cfg_entry_provider()
        db_cls: type[IAstrbotDatabase] = db_provider()
        broker_instance: BROKER_TYPE = BROKER()
        # 注入依赖到本模块实例
        self.broker: BROKER_TYPE = broker_instance
        self.paths: IAstrbotPaths = paths_cls.root(self.pypi_name)
        self.config: IAstrbotConfig = config_cls.getConfig(self.pypi_name)
        self.db_cls: type[IAstrbotDatabase] = db_cls # 需要连接时调用 connect 方法获取实例
        self.cfg_entry_cls: type[IAstrbotConfigEntry] = cfg_entry_cls
        # 初始化数据库连接
        self.db : IAstrbotDatabase = self.db_cls.init_db(self.paths.data / "canary_web.db", Base)

        self.cfg_web: IAstrbotConfigEntry = self.config.bindEntry(
            entry=self.cfg_entry_cls.bind(
                pypi_name=self.pypi_name,
                group="basic",
                name="common",
                default=AstrbotCanaryWebConfig(
                    webroot=self.paths.astrbot_root / "webroot",
                    host="127.0.0.1",
                    port=6185
                ),
                description="Web UI 监听的主机地址",
                config_dir=self.paths.config
            )
        )

        logger.info(f"Web Config initialized: {self.cfg_web.value.webroot.absolute()}, {self.cfg_web.value.host}:{self.cfg_web.value.port}")

        if not AstrbotCanaryFrontend.ensure(self.cfg_web.value.webroot.absolute()):
            raise FileNotFoundError("Failed to ensure frontend files in webroot.")
        logger.info(f"Frontend files are ready in {self.cfg_web.value.webroot.absolute()}")

        # 初始化 FastAPI 应用并挂载子路由
        self.app = FastAPI()
        # 挂载静态文件和路由
        self.app.mount(
            path="/home", 
            app=StaticFiles(directory=self.cfg_web.value.webroot / "dist" , html=True), 
            name="index.html"
        )
        self.app.mount(
            path="/assets",
            app=StaticFiles(directory=str(self.cfg_web.value.webroot / "dist" / "assets")),
            name="assets",
        )
        self.app.mount(
            path="/favicon.svg",
            app=StaticFiles(directory=str(self.cfg_web.value.webroot / "dist")),
            name="favicon.svg",
        )
        self.app.mount(
            path="/_redirects",
            app=StaticFiles(directory=str(self.cfg_web.value.webroot / "dist")),
            name="_redirects",
        )

        @self.app.get("/", include_in_schema=False)
        async def index() -> RedirectResponse: 
            return RedirectResponse(url="/home")

        logger.debug(f"debug:{index} -- 纯为了消除未存取&警告lol")

        # 嵌套挂载子路由 并注入全部依赖
        self.app.include_router(api_router)

        Response.deps["MODULE"] = self
        # 准备启动...

    def Start(self) -> None:
        logger.info(f"{self.name} v{self.version} has started.")
        # Use uvicorn to run FastAPI app
        # 在后台线程中启动 uvicorn，避免阻塞主线程
        uvicorn.run(
            self.app,
            host=str(self.cfg_web.value.host),
            port=int(self.cfg_web.value.port),
            log_level="info",
        )


    def OnDestroy(self) -> None:
        logger.info(f"{self.name} v{self.version} is being destroyed.")
