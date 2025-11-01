from __future__ import annotations

from importlib.metadata import PackageMetadata
from logging import Logger, getLogger

from astrbot_canary_api import (
    AstrbotModuleType,
    IAstrbotModule,
)

logger: Logger = getLogger("astrbot.module.tui")


class AstrbotCanaryTui(IAstrbotModule):
    pypi_name: str = "astrbot_canary_tui"
    name: str = "canary_tui"
    module_type: AstrbotModuleType = AstrbotModuleType.TUI
    info: PackageMetadata | None = None

    @classmethod
    def Awake(cls) -> None:
        logger.info("%s is awakening.", cls.name)

    @classmethod
    def Start(cls) -> None:
        logger.info("%s has started.", cls.name)

    @classmethod
    def OnDestroy(cls) -> None:
        logger.info(
            "%s is being destroyed.",
            cls.name,
        )
