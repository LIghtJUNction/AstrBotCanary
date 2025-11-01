from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging import Logger, getLogger
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import uvicorn
from astrbot_canary_api import (
    AstrbotModuleType,
    ContainerRegistry,
    IAstrbotConfigEntry,
    IAstrbotLogHandler,
    IAstrbotModule,
    IAstrbotPaths,
    moduleimpl,
)
from dishka import make_async_container
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi_radar import Radar
from pydantic import BaseModel
from taskiq import AsyncBroker

from astrbot_canary_web.api import api_router
from astrbot_canary_web.api.provider import WebAPIProvider
from astrbot_canary_web.frontend import AstrbotCanaryFrontend

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from importlib.metadata import PackageMetadata
logger: Logger = getLogger("astrbot.module.web")


class AstrbotCanaryWebConfig(BaseModel):
    webroot: str
    host: str = "127.0.0.1"
    port: int = 6185
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    jwt_exp_days: int = 7


class AstrbotCanaryWeb(IAstrbotModule):
    Paths: type[IAstrbotPaths] | None = None
    ConfigEntry: type[IAstrbotConfigEntry[AstrbotCanaryWebConfig]] | None = None

    pypi_name: str = "astrbot_canary_web"
    name: str = "canary_web"
    module_type: AstrbotModuleType = AstrbotModuleType.WEB
    info: PackageMetadata | None = None

    cfg_web: IAstrbotConfigEntry[AstrbotCanaryWebConfig] | None = None

    def __init__(
        self,
        paths: IAstrbotPaths | None = None,
        cfg_web: IAstrbotConfigEntry[AstrbotCanaryWebConfig] | None = None,
        app: FastAPI | None = None,
        broker: AsyncBroker | None = None,
        pypi_name: str = "astrbot_canary_web",
        name: str = "canary_web",
        module_type: AstrbotModuleType = AstrbotModuleType.WEB,
        info: PackageMetadata | None = None,
    ) -> None:
        self.paths: IAstrbotPaths | None = paths
        self.cfg_web: IAstrbotConfigEntry[AstrbotCanaryWebConfig] | None = cfg_web
        self.app: FastAPI | None = app
        self.broker: AsyncBroker | None = broker
        self.pypi_name: str = pypi_name
        self.name: str = name
        self.module_type: AstrbotModuleType = module_type
        self.info: PackageMetadata | None = info

    @classmethod
    @moduleimpl(trylast=True)
    def Awake(
        cls,
    ) -> None:
        logger.info(
            "%s is awakening.",
            cls.name,
        )

        # Get dependencies from sync container (proper way for sync context)
        core_container = ContainerRegistry.get_sync("core")
        paths_instance: IAstrbotPaths = core_container.get(IAstrbotPaths)

        cls.ConfigEntry = core_container.get(dependency_type=type(IAstrbotConfigEntry))
        # Get broker (may be None if not available)
        try:
            from taskiq import AsyncBroker
            cls.broker = core_container.get(AsyncBroker)
        except Exception:
            cls.broker = None

        cls.cfg_web = cls.ConfigEntry.bind(
            group="basic",
            name="common",
            default=AstrbotCanaryWebConfig(
                webroot=str(paths_instance.root / "webroot"),
                host="127.0.0.1",
                port=6185,
                log_level="info",
                jwt_exp_days=7,
            ),
            description="Web UI 监听的主机地址",
            cfg_dir=paths_instance.config,
        )

        logger.info(
            "Web Config initialized: %s, %s:%s",
            Path(cls.cfg_web.value.webroot).absolute(),
            cls.cfg_web.value.host,
            cls.cfg_web.value.port,
        )

        # Create WebAPIProvider and build web component container

        # Create and configure web API provider
        api_provider = WebAPIProvider()

        # Get log handler from core container and configure API provider
        try:
            log_handler = core_container.get(IAstrbotLogHandler)
            api_provider.set_log_handler(log_handler)
        except Exception:
            logger.warning("Could not get log handler from core container")

        api_provider.set_jwt_exp_days(cls.cfg_web.value.jwt_exp_days)

        # Create independent async container for web component
        web_container = make_async_container(api_provider, FastapiProvider())
        ContainerRegistry.register_async("web", web_container)

        if not AstrbotCanaryFrontend.ensure(Path(cls.cfg_web.value.webroot).absolute()):
            msg = "Failed to ensure frontend files in webroot."
            raise FileNotFoundError(msg)
        logger.info(
            "Frontend files are ready in %s",
            Path(cls.cfg_web.value.webroot).absolute(),
        )

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
            """以下为测试代码-TODO: 删除."""
            logger.info("启动broker ...,%s", app)
            if cls.broker is not None:
                await cls.broker.startup()
            yield
            logger.info("关闭broker ...")
            if cls.broker is not None:
                await cls.broker.shutdown()
                logger.info("关闭backend服务 ...")
                await cls.broker.result_backend.shutdown()

        # 初始化 FastAPI 应用并挂载子路由

        cls.app = FastAPI(
            title="AstrBot Canary Web",
            description="AstrBot Canary Web API",
            version="0.1.0",
            default_response_class=ORJSONResponse,
            lifespan=lifespan,
        )

        # Register dishka async container to FastAPI app
        async_container = ContainerRegistry.get_async("core")
        setup_dishka(container=async_container, app=cls.app)
        # Note: Radar initialization requires a database engine
        # For now, skip Radar initialization if engine is not available
        try:
            from sqlalchemy import create_engine
            # Create in-memory SQLite engine for monitoring
            engine = create_engine("sqlite:///:memory:")
            radar = Radar(app=cls.app, db_engine=engine)
            radar.create_tables()
            logger.info("Radar monitoring initialized.")
        except ImportError:
            logger.warning("SQLAlchemy not available, skipping Radar initialization")

        # 嵌套挂载子路由(先注册 API 路由,保证 API 优先匹配)
        cls.app.include_router(api_router)

        cls.app.mount(
            path="/",
            app=StaticFiles(
                directory=Path(cls.cfg_web.value.webroot) / "dist",
                html=True,
            ),
            name="frontend",
        )

        # broker already fetched from core provider above, no need to repeat

    @classmethod
    @moduleimpl
    def Start(cls) -> None:
        # 使用 Uvicorn 启动 FastAPI 应用
        logger.info(
            "访问监控面板:http://%s:%s/__radar/",
            cls.cfg_web.value.host if cls.cfg_web else "127.0.0.1",
            cls.cfg_web.value.port if cls.cfg_web else 6185,
        )
        logger.info(
            "访问DOCS:http://%s:%s/docs",
            cls.cfg_web.value.host if cls.cfg_web else "127.0.0.1",
            cls.cfg_web.value.port if cls.cfg_web else 6185,
        )
        if cls.app is None:
            msg = "FastAPI app未初始化"
            raise RuntimeError(msg)
        uvicorn.run(
            app=cls.app,
            host=cls.cfg_web.value.host if cls.cfg_web else "127.0.0.1",
            port=cls.cfg_web.value.port if cls.cfg_web else 6185,
            log_level=cls.cfg_web.value.log_level if cls.cfg_web else "info",
        )
    @classmethod
    @moduleimpl
    def OnDestroy(cls) -> None:
        logger.info("%s is being destroyed.", cls.name)
