from astrbot_canary_api import (
    IAstrbotModule,
    IAstrbotPaths,
    AstrbotPaths,
    AstrbotConfig,
)
from astrbot_canary_api.enums import AstrBotModuleType
from logging import getLogger , Logger

logger: Logger = getLogger("astrbot_canary.module.loader")

class AstrbotLoader():
    name = "canary_loader"
    pypi_name = "astrbot_canary_loader"
    module_type = AstrBotModuleType.LOADER
    version = "1.0.0"
    authors = ["LIghtJUNction"]
    description = "Loader module for Astrbot Canary."
    enabled = True

    def Awake(self) -> None:
        logger.info(f"{self.name} v{self.version} is awakening.")
        # 初始化Paths和Config
        self.paths: IAstrbotPaths = AstrbotPaths.root(self.pypi_name)
        self.config: AstrbotConfig = AstrbotConfig.getConfig(self.pypi_name)

        # 绑定配置
        ...

    def Start(self) -> None:
        logger.info(f"{self.name} v{self.version} is starting.")
        pass

    def OnDestroy(self) -> None:
        logger.info(f"{self.name} v{self.version} is shutting down.")
        pass