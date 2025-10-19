from contextlib import asynccontextmanager
from importlib.metadata import PackageMetadata
from pathlib import Path
# import uvicorn
from logging import getLogger , Logger
from typing import Literal
from fastapi.responses import ORJSONResponse
from fastapi_radar import Radar #type: ignore 用于监控
from taskiq import AsyncBroker, AsyncTaskiqDecoratedTask, AsyncTaskiqTask, TaskiqResult
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

logger: Logger = getLogger("astrbot.module.web")

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

        if not AstrbotCanaryFrontend.ensure(Path(cls.cfg_web.value.webroot).absolute()):
            raise FileNotFoundError("Failed to ensure frontend files in webroot.")
        logger.info(f"Frontend files are ready in {Path(cls.cfg_web.value.webroot).absolute()}")


        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """ 以下为测试代码-TODO: 删除 """
            logger.info("启动broker ...")
            await cls.broker.startup()
            logger.info("启动backend服务 ...")
            await cls.broker.result_backend.startup()
            echo_task_handler: AsyncTaskiqDecoratedTask[..., str] | None = cls.broker.find_task("astrbot://echo")
            if echo_task_handler is None:
                raise ValueError("无法找到任务 astrbot://echo !!! 请检查核心模块!!!")
            task: AsyncTaskiqTask[str] = await echo_task_handler.kiq("Hello from Astrbot Canary Web!")
            result: TaskiqResult[str] = await task.wait_result()
            logger.info(f"测试任务 astrbot://echo 返回结果：{result.return_value}")

            yield
            logger.info("关闭broker ...")
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

        engine = cls.database.engine
        if engine is None:
            raise ValueError("Database engine is not initialized!")
        radar = Radar( app=cls.app, db_engine=engine)
        radar.create_tables()
        logger.info("Radar monitoring initialized.")

        # 嵌套挂载子路由（先注册 API 路由，保证 API 优先匹配）
        cls.app.include_router(api_router)

        cls.app.mount(
            path="/",
            app=StaticFiles(directory=Path(cls.cfg_web.value.webroot) / "dist", html=True),
            name="frontend",
        )

        cls.broker: AsyncBroker = AstrbotInjector.get("broker")  
        
    @classmethod
    @moduleimpl
    def Start(cls) -> None:
        # 使用 Uvicorn 启动 FastAPI 应用
        logger.info(f"访问监控面板：http://{cls.cfg_web.value.host}:{cls.cfg_web.value.port}/__radar/")
        logger.info(f"访问DOCS：http://{cls.cfg_web.value.host}:{cls.cfg_web.value.port}/docs")
        uvicorn.run(
			cls.app,
			host=cls.cfg_web.value.host,
			port=cls.cfg_web.value.port,
            log_level=cls.cfg_web.value.log_level,
		)

    @classmethod
    @moduleimpl
    def OnDestroy(cls) -> None:
        logger.info(f"{cls.info.get('name')} is being destroyed.")