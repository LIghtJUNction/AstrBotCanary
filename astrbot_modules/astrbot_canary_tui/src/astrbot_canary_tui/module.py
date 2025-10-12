from astrbot_canary_api import IAstrbotModule
from astrbot_canary_api.enum import AstrBotModuleType
from logging import getLogger , Logger
logger: Logger = getLogger("astrbot_canary.module.tui")

class AstrbotCanaryTui(IAstrbotModule):
    name = "canary_tui"
    pypi_name = "astrbot_canary_tui"
    module_type = AstrBotModuleType.TUI
    version = "0.1.0"
    authors = ["LIghtJUNction"]
    description = "TUI module for Astrbot Canary."
    enabled = True

    def Awake(self) -> None:
        logger.info(f"{self.name} v{self.version} is awakening.")

    def Start(self) -> None:
        logger.info(f"{self.name} v{self.version} has started.")

    def OnDestroy(self) -> None:
        logger.info(f"{self.name} v{self.version} is being destroyed.")