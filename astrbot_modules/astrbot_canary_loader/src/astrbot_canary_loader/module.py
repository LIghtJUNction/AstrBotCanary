from __future__ import annotations

from logging import Logger, getLogger

from astrbot_canary_api import AstrbotModuleType, moduleimpl
from astrbot_canary_api.decorators import AstrbotModule

logger: Logger = getLogger("astrbot.module.loader")


@AstrbotModule("astrbot-canary-loader", "canary_loader", AstrbotModuleType.LOADER)
class AstrbotLoader:
    info: None = None

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
