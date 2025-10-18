...
from logging import getLogger , Logger
logger: Logger = getLogger("astrbot.module.tui")

class AstrbotCanaryTui():
    ...

    def Awake(self) -> None:
        logger.info(f"{self.name} v{self.version} is awakening.")

    def Start(self) -> None:
        logger.info(f"{self.name} v{self.version} has started.")

    def OnDestroy(self) -> None:
        logger.info(f"{self.name} v{self.version} is being destroyed.")