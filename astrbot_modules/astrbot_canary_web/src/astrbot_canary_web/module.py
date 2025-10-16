from fastapi import FastAPI
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
    name: str = "canary_web"
    pypi_name: str = "astrbot_canary_web"
    module_type: AstrBotModuleType = AstrBotModuleType.WEB
    version: str = "0.1.0"
    authors: list[str] = ["LIghtJUNction"]
    description: str = "Web UI module for Astrbot Canary."

    enabled: bool = True

    def Awake(
            self,
        ) -> None:
        logger.info(f"{self.name} v{self.version} is awakening.")

        # 初始化 Paths 和 Config（与 loader 风格一致）
        self.paths: IAstrbotPaths = paths_cls.getPaths(self.pypi_name)
        self.config: IAstrbotConfig = config_cls.getConfig(self.pypi_name)

        # 延迟数据库连接：保存类以在需要时调用
        self.db_cls: type[IAstrbotDatabase] = db_cls
        self.cfg_entry_cls: type[IAstrbotConfigEntry] = cfg_entry_cls

        # Broker 实例
        self.broker: BROKER_TYPE = broker

        # 初始化数据库连接（实际建立）
        self.db: IAstrbotDatabase = self.db_cls.init_db(self.paths.data / "canary_web.db", Base)

        # 绑定 Web 模块的配置项
        self.cfg_web: IAstrbotConfigEntry = self.config.bindEntry(
            entry=self.cfg_entry_cls.bind(
                pypi_name=self.pypi_name,
                group="basic",
                name="common",
                default=AstrbotCanaryWebConfig(
                    webroot=self.paths.astrbot_root / "webroot",
                    host="127.0.0.1",
                    port=6185,
                    jwt_exp_days=7
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

        # 嵌套挂载子路由（先注册 API 路由，保证 API 优先匹配）
        self.app.include_router(api_router)

        self.app.mount(
            path="/",
            app=StaticFiles(directory=self.cfg_web.value.webroot / "dist", html=True),
            name="frontend",
        )

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
