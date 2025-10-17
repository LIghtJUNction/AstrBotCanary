from importlib.metadata import PackageMetadata
from astrbot_canary_api import (
    moduleimpl,
)
from astrbot_canary_api.decorators import AstrbotModule

# from .tasks import AstrbotCanaryLoaderTasks

from logging import getLogger , Logger

logger: Logger = getLogger("astrbot_canary.module.loader")

@AstrbotModule(
    pypi_name="astrbot_canary_loader",
)
class AstrbotLoader():
    info : PackageMetadata

    @classmethod
    @moduleimpl
    def Awake(
            cls, 
        ) -> None:

        logger.info(f"{cls.info} is awakening.")

    @classmethod
    @moduleimpl
    def Start(cls) -> None:
        logger.info(f"{cls.info} is starting.")
        # cls.tasks: AstrbotCanaryLoaderTasks = AstrbotCanaryLoaderTasks.register(cls.broker)

    @classmethod
    @moduleimpl
    def OnDestroy(cls) -> None:
        logger.info(f"{cls.info} is shutting down.")
        pass

