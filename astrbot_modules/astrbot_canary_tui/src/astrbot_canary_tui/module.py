from importlib.metadata import PackageMetadata
from logging import Logger, getLogger

from astrbot_canary_api import AstrbotModuleType
from astrbot_canary_api.decorators import AstrbotModule

logger: Logger = getLogger("astrbot.module.tui")


@AstrbotModule("astrbot_canary_tui", "canary_tui", AstrbotModuleType.TUI)
class AstrbotCanaryTui:
    info: PackageMetadata

    @classmethod
    def Awake(cls) -> None:
        logger.info(f"{cls.info.get('Name')} is awakening.")

    @classmethod
    def Start(cls) -> None:
        logger.info(f"{cls.info.get('Name')} has started.")

    @classmethod
    def OnDestroy(cls) -> None:
        logger.info(f"{cls.info.get('Name')} is being destroyed.")
