from importlib.metadata import PackageMetadata
from astrbot_canary_api import (
    AstrbotModuleType,
    moduleimpl,
)
from astrbot_canary_api.decorators import AstrbotModule

# from .tasks import AstrbotCanaryLoaderTasks

from logging import getLogger , Logger

logger: Logger = getLogger("astrbot_canary.module.loader")

@AstrbotModule("astrbot_canary_loader","canary_loader",AstrbotModuleType.LOADER)
class AstrbotLoader():
    info : PackageMetadata

    @classmethod
    @moduleimpl
    def Awake(
            cls, 
        ) -> None:

        logger.info(f"{cls.info.get("name")} is awakening.")

    @classmethod
    @moduleimpl
    def Start(
        cls
        ) -> None:
        logger.info(f"{cls.info.get("name")} is starting.")

    @classmethod
    @moduleimpl
    def OnDestroy(
        cls
        ) -> None:
        logger.info(f"{cls.info.get("name")} is shutting down.")
        pass

