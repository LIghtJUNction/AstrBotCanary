from __future__ import annotations

from importlib.metadata import PackageMetadata
from logging import Logger, getLogger

from astrbot_canary_api import (
    AstrbotModuleType,
    IAstrbotModule,
    moduleimpl,
)

logger: Logger = getLogger("astrbot.module.loader")


class AstrbotLoader(IAstrbotModule):
    pypi_name: str = "astrbot_canary_loader"
    name: str = "canary_loader"
    module_type: AstrbotModuleType = AstrbotModuleType.LOADER
    info: PackageMetadata | None = None

    def __call__(self: AstrbotLoader) -> AstrbotLoader:
        return self

    @classmethod
    @moduleimpl
    def Awake(
        cls,
    ) -> None:
        logger.info(
            "%s is awakening.",
            getattr(cls.info, "get", lambda _: "unknown")("name")
            if cls.info
            else "unknown",
        )

    @classmethod
    @moduleimpl
    def Start(
        cls,
    ) -> None:
        logger.info(
            "%s is starting.",
            getattr(cls.info, "get", lambda _: "unknown")("name")
            if cls.info
            else "unknown",
        )

    @classmethod
    @moduleimpl
    def OnDestroy(
        cls,
    ) -> None:
        logger.info(
            "%s is shutting down.",
            getattr(cls.info, "get", lambda _: "unknown")("name")
            if cls.info
            else "unknown",
        )
