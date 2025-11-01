from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging import Logger, getLogger
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import uvicorn
from astrbot_canary_api import (
    AstrbotModuleType,
    IAstrbotConfigEntry,
    IAstrbotModule,
    IAstrbotPaths,
    ProviderRegistry,
    moduleimpl,
)
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi_radar import Radar
from pydantic import BaseModel
from taskiq import AsyncBroker

from astrbot_canary_web.api import api_router
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

        # 从 dishka 容器获取依赖
        container = ProviderRegistry.get_container()
        paths_instance: IAstrbotPaths = container.get(IAstrbotPaths)
        cls.ConfigEntry = container.get(type[IAstrbotConfigEntry])
        # broker 可能为 None，如果无法获取则设为 None
        try:
            cls.broker = container.get(AsyncBroker)
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
        # 从 ProviderRegistry 获取 core provider 来配置 jwt_exp_days
        try:
            core_provider = ProviderRegistry.get("core")
            if hasattr(core_provider, "jwt_exp_days"):
                core_provider.jwt_exp_days = cls.cfg_web.value.jwt_exp_days
        except KeyError:
            logger.warning("Core provider not found in ProviderRegistry")

        # 创建并注册 WebAPIProvider 到 ProviderRegistry
        from astrbot_canary_web.api.provider import WebAPIProvider
        api_provider = WebAPIProvider()
        # 从 core provider 获取 log_handler 并设置到 api_provider
        try:
            core_provider = ProviderRegistry.get("core")
            if hasattr(core_provider, "log_handler"):
                api_provider.set_log_handler(core_provider.log_handler)
            api_provider.set_jwt_exp_days(cls.cfg_web.value.jwt_exp_days)
        except KeyError:
            logger.warning("Core provider not found, log handler not set")
        ProviderRegistry.register("web_api", api_provider)

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

        # 从 ProviderRegistry 获取 broker
        try:
            core_provider = ProviderRegistry.get("core")
            if hasattr(core_provider, "broker"):
                cls.broker = core_provider.broker
        except KeyError:
            logger.warning(
                "Core provider not found in ProviderRegistry, broker not set",
            )

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
