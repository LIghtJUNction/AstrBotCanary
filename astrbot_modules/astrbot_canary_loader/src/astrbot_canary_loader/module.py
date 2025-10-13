from dependency_injector.containers import Container
from dependency_injector.providers import Provider
from astrbot_canary_api.types import BROKER_TYPE
from astrbot_canary_api import (
    IAstrbotConfig,
    IAstrbotPaths,
)
from astrbot_canary_api.enums import AstrBotModuleType
from logging import getLogger , Logger

from astrbot_canary_api.interface import IAstrbotDatabase

logger: Logger = getLogger("astrbot_canary.module.loader")

class AstrbotLoader():
    name = "canary_loader"
    pypi_name = "astrbot_canary_loader"
    module_type = AstrBotModuleType.LOADER
    version = "1.0.0"
    authors = ["LIghtJUNction"]
    description = "Loader module for Astrbot Canary."
    enabled = True

    def Awake(self, deps: Container | None = None) -> None:
        logger.info(f"{self.name} v{self.version} is awakening.")
        # 初始化Paths和Config
        if deps is None:
            raise ValueError("Dependency container is required for AstrbotLoader.")
        logger.debug(f"Dependency container attributes: {[n for n in dir(deps) if not n.startswith('_')]}")

        paths_provider: Provider[type[IAstrbotPaths]] = deps.AstrbotPaths
        config_provider: Provider[type[IAstrbotConfig]] = deps.AstrbotConfig
        db_provider: Provider[type[IAstrbotDatabase]] = deps.AstrbotDatabase
        BROKER: Provider[BROKER_TYPE] = deps.BROKER

        paths_cls: type[IAstrbotPaths] = paths_provider()
        config_cls: type[IAstrbotConfig] = config_provider()
        db_cls: type[IAstrbotDatabase] = db_provider()
        broker_instance: BROKER_TYPE = BROKER()
    
        self.paths: IAstrbotPaths = paths_cls.root(self.pypi_name)
        self.config: IAstrbotConfig = config_cls.getConfig(self.pypi_name)
        self.db_cls: type[IAstrbotDatabase] = db_cls # 需要连接时调用 connect 方法获取实例
        self.broker: BROKER_TYPE = broker_instance

        logger.info(f"Paths initialized at {self.paths.astrbot_root}")
        logger.info(f"Config initialized for {self.config}")
        logger.info(f"Database class ready: {self.db_cls}")
        logger.info(f"Broker instance ready: {self.broker}")


        # 绑定配置
        ...

    def Start(self) -> None:
        logger.info(f"{self.name} v{self.version} is starting.")
        pass

    def OnDestroy(self) -> None:
        logger.info(f"{self.name} v{self.version} is shutting down.")
        pass

