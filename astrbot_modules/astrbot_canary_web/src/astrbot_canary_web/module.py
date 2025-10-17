from importlib.metadata import PackageMetadata

import uvicorn
from logging import getLogger , Logger

from astrbot_canary_api import moduleimpl
from astrbot_canary_api.decorators import AstrbotModule

# from astrbot_canary_web.api import api_router

logger: Logger = getLogger("astrbot_canary.module.web")

@AstrbotModule(
    pypi_name="astrbot_canary_web",
)
class AstrbotCanaryWeb():
    info: PackageMetadata

    @moduleimpl
    @classmethod
    def Awake(
            cls,
        ) -> None:
        logger.info(f"{cls.info} is awakening.")

        # # 绑定 Web 模块的配置项
        # self.cfg_web: IAstrbotConfigEntry = self.config.bindEntry(
        #     entry=self.cfg_entry_cls.bind(
        #         pypi_name=self.pypi_name,
        #         group="basic",
        #         name="common",
        #         default=AstrbotCanaryWebConfig(
        #             webroot=self.paths.astrbot_root / "webroot",
        #             host="127.0.0.1",
        #             port=6185,
        #             jwt_exp_days=7
        #         ),
        #         description="Web UI 监听的主机地址",
        #         config_dir=self.paths.config
        #     )
        # )
# 
        # logger.info(f"Web Config initialized: {self.cfg_web.value.webroot.absolute()}, {self.cfg_web.value.host}:{self.cfg_web.value.port}")
# 
        # if not AstrbotCanaryFrontend.ensure(self.cfg_web.value.webroot.absolute()):
        #     raise FileNotFoundError("Failed to ensure frontend files in webroot.")
        # logger.info(f"Frontend files are ready in {self.cfg_web.value.webroot.absolute()}")
# 
        # # 初始化 FastAPI 应用并挂载子路由
        # self.app = FastAPI()
# 
        # # 嵌套挂载子路由（先注册 API 路由，保证 API 优先匹配）
        # self.app.include_router(api_router)
# 
        # self.app.mount(
        #     path="/",
        #     app=StaticFiles(directory=self.cfg_web.value.webroot / "dist", html=True),
        #     name="frontend",
        # )
# 
        # Response.deps["MODULE"] = self
        # # 准备启动...

    @moduleimpl
    @classmethod
    def Start(cls) -> None:
        logger.info(f"{cls.name} v{cls.version} has started.")
        # Use uvicorn to run FastAPI app
        # 在后台线程中启动 uvicorn，避免阻塞主线程
        uvicorn.run(
            cls.app,
            host=str(cls.cfg_web.value.host),
            port=int(cls.cfg_web.value.port),
            log_level="info",
        )

    @moduleimpl
    @classmethod
    def OnDestroy(cls) -> None:
        logger.info(f"{cls.name} v{cls.version} is being destroyed.")
