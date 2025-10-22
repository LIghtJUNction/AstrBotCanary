from importlib.metadata import PackageMetadata
from logging import Logger, getLogger

from astrbot_canary_api import AstrbotModuleType
from astrbot_canary_api.decorators import AstrbotModule

logger: Logger = getLogger("astrbot.module.tui")


@AstrbotModule("astrbot_canary_tui", "canary_tui", AstrbotModuleType.TUI)
class AstrbotCanaryTui:
    info: PackageMetadata | None = None

    @classmethod
    def Awake(cls) -> None:
        logger.info("%s is awakening.", cls.info.get("Name") if cls.info else "unknown")

    @classmethod
    def Start(cls) -> None:
        logger.info("%s has started.", cls.info.get("Name") if cls.info else "unknown")

    @classmethod
    def OnDestroy(cls) -> None:
        logger.info(
            "%s is being destroyed.",
            cls.info.get("Name") if cls.info else "unknown",
        )
