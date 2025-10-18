from importlib.metadata import PackageMetadata
from pathlib import Path
# import uvicorn
from logging import getLogger , Logger
from typing import Literal
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from astrbot_canary_api import AstrbotModuleType, IAstrbotConfigEntry, IAstrbotPaths, moduleimpl
from astrbot_canary_api.decorators import AstrbotInjector, AstrbotModule
from astrbot_canary_api.interface import IAstrbotDatabase
from astrbot_canary_web.api import api_router
from astrbot_canary_web.frontend import AstrbotCanaryFrontend

# from astrbot_canary_web.api import api_router

logger: Logger = getLogger("astrbot_canary.module.web")

class AstrbotCanaryWebConfig(BaseModel):
    webroot: str
    host: str = "127.0.0.1"
    port: int = 6185
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    jwt_exp_days: int = 7

@AstrbotModule("astrbot_canary_web", "canary_web", AstrbotModuleType.WEB)
class AstrbotCanaryWeb():

    info: PackageMetadata

    ConfigEntry: type[IAstrbotConfigEntry[AstrbotCanaryWebConfig]]
    paths: IAstrbotPaths
    database: IAstrbotDatabase

    @classmethod
    @moduleimpl(trylast=True)
    def Awake(
            cls,
        ) -> None:
        logger.info(f"{cls.info.get("name")} is awakening.")

        # # 绑定 Web 模块的配置项
        cls.cfg_web: IAstrbotConfigEntry[AstrbotCanaryWebConfig] = cls.ConfigEntry.bind(
            group="basic",
            name="common",
            default=AstrbotCanaryWebConfig(
                webroot=str(cls.paths.astrbot_root / "webroot"),
                host="127.0.0.1",
                    port=6185,
                    log_level="info",
                    jwt_exp_days=7
                ),
                description="Web UI 监听的主机地址",
                cfg_dir=cls.paths.config
            )


        logger.info(f"Web Config initialized: {Path(cls.cfg_web.value.webroot).absolute()}, {cls.cfg_web.value.host}:{cls.cfg_web.value.port}")
        AstrbotInjector.set("JWT_EXP_DAYS", cls.cfg_web.value.jwt_exp_days)
        AstrbotInjector.set("CANARY_WEB_DB", cls.database)
        logger.info(f"DI: JWT_EXP_DAYS={cls.cfg_web.value.jwt_exp_days}, CANARY_WEB_DB={cls.database}")
        if not AstrbotCanaryFrontend.ensure(Path(cls.cfg_web.value.webroot).absolute()):
            raise FileNotFoundError("Failed to ensure frontend files in webroot.")
        logger.info(f"Frontend files are ready in {Path(cls.cfg_web.value.webroot).absolute()}")

        # 初始化 FastAPI 应用并挂载子路由
        cls.app = FastAPI()

        # 嵌套挂载子路由（先注册 API 路由，保证 API 优先匹配）
        cls.app.include_router(api_router)

        cls.app.mount(
            path="/",
            app=StaticFiles(directory=Path(cls.cfg_web.value.webroot) / "dist", html=True),
            name="frontend",
        )

        # Response.deps["MODULE"] = cls
        # 准备启动...

    @classmethod
    @moduleimpl
    def Start(cls) -> None:
        # 使用 Uvicorn 启动 FastAPI 应用
        uvicorn.run(
			cls.app,
			host=cls.cfg_web.value.host,
			port=cls.cfg_web.value.port,
            log_level=cls.cfg_web.value.log_level,
		)

    @classmethod
    @moduleimpl
    def OnDestroy(cls) -> None:
        ...