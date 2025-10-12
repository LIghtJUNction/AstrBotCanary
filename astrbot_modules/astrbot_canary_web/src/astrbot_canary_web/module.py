from astrbot_canary_api import IAstrbotModule
from astrbot_canary_api.enums import AstrBotModuleType
from logging import getLogger , Logger

logger: Logger = getLogger("astrbot_canary.module.web")

class AstrbotCanaryWeb(IAstrbotModule):
    name = "canary_web"
    pypi_name = "astrbot_canary_web"
    module_type = AstrBotModuleType.WEB
    version = "0.1.0"
    authors = ["LIghtJUNction"]
    description = "Web UI module for Astrbot Canary."
    enabled = True

    def Awake(self) -> None:
        logger.info(f"{self.name} v{self.version} is awakening.")

    def Start(self) -> None:
        logger.info(f"{self.name} v{self.version} has started.")

    def OnDestroy(self) -> None:
        logger.info(f"{self.name} v{self.version} is being destroyed.")
