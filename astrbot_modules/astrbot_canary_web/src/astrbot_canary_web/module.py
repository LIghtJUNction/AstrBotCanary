from dependency_injector.containers import Container
from dependency_injector.providers import Provider

from astrbot_canary.core.models import Base
from astrbot_canary_api import IAstrbotConfig, IAstrbotConfigEntry
from astrbot_canary_api.enums import AstrBotModuleType
from logging import getLogger , Logger

from astrbot_canary_api.interface import IAstrbotDatabase, IAstrbotPaths
from astrbot_canary_api.types import BROKER_TYPE
from astrbot_canary_web.config import AstrbotCanaryWebConfig
from astrbot_canary_web.frontend import AstrbotCanaryFrontend

from .app import AstrbotCanaryWebApp

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
        # 注入依赖
        AstrbotCanaryWebApp.web_app.inject_global(BROKER=broker_instance) # type: ignore

        self.broker: BROKER_TYPE = broker_instance
        self.paths: IAstrbotPaths = paths_cls.root(self.pypi_name)
        self.config: IAstrbotConfig = config_cls.getConfig(self.pypi_name)
        self.db_cls: type[IAstrbotDatabase] = db_cls # 需要连接时调用 connect 方法获取实例
        self.cfg_entry_cls: type[IAstrbotConfigEntry] = cfg_entry_cls

        # 初始化数据库连接
        self.db : IAstrbotDatabase = self.db_cls.init_db(self.paths.data / "canary_web.db", Base)
        # 注入数据库依赖
        AstrbotCanaryWebApp.db = self.db

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

        # 把已经初始化的属性注入到 web app wrapper 上，确保 self.* 已经存在
        AstrbotCanaryWebApp.cfg_web = self.cfg_web
        AstrbotCanaryWebApp.paths = self.paths
        AstrbotCanaryWebApp.broker = self.broker

        # 绑定前端 （bug）
        # https://github.com/sparckles/Robyn/issues/1251
        AstrbotCanaryWebApp.web_app.serve_directory(route="/", directory_path=str(AstrbotCanaryWebApp.cfg_web.value.webroot.absolute() / "dist"), index_file="index.html",show_files_listing=True)

        # 初始路由
        AstrbotCanaryWebApp.init()



    def Start(self) -> None:
        logger.info(f"{self.name} v{self.version} has started.")
        AstrbotCanaryWebApp.web_app.start(host=self.cfg_web.value.host, port=self.cfg_web.value.port)

    def OnDestroy(self) -> None:
        logger.info(f"{self.name} v{self.version} is being destroyed.")
