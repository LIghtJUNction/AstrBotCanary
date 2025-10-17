from importlib.metadata import PackageMetadata
from astrbot_canary_api import (
    AstrbotModuleType,
    IAstrbotConfig,
    IAstrbotPaths,
    IAstrbotDatabase,
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

    @moduleimpl
    @classmethod
    def Awake(
            cls, 
        ) -> None:

        logger.info(f"{cls.info} is awakening.")
        # 初始化Paths和Config

        # logger.info(f"Paths initialized at {self.paths.astrbot_root}")
        # logger.info(f"Config initialized for {self.config}")
        # logger.info(f"Database class ready: {self.db_cls}")
        # logger.info(f"Broker instance ready: {self.broker}")

        # 绑定配置
        ...

        # 绑定任务
        # AstrbotCanaryLoaderTasks.register(self.broker)

    @moduleimpl
    @classmethod
    def Start(cls) -> None:
        logger.info(f"{cls.info} is starting.")
        # cls.tasks: AstrbotCanaryLoaderTasks = AstrbotCanaryLoaderTasks.register(cls.broker)

    @moduleimpl
    @classmethod
    def OnDestroy(cls) -> None:
        logger.info(f"{cls.info} is shutting down.")
        pass

