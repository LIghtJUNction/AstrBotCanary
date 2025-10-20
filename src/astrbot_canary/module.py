"""
astrbot_canary 核心模块
注意：不要在本模块内写异步函数
异步循环只能在最后一个启动的模块内编写

比如web模块
请务必使用await broker.startup()等待broker启动完成

"""

from importlib.metadata import PackageMetadata
from logging import getLogger

from astrbot_canary_api import (
    AstrbotModuleType,
    IAstrbotConfigEntry,
    IAstrbotDatabase,
    IAstrbotPaths,
    moduleimpl,
)
from astrbot_canary_api.decorators import AstrbotModule
from pydantic import BaseModel

"""
依赖抽象，而非具体
"""

logger = getLogger("astrbot.module.core")


class AstrbotCoreConfig(BaseModel):
    """
    核心模块配置项
    """

    ...


@AstrbotModule("astrbot_canary", "canary_core", AstrbotModuleType.CORE)
class AstrbotCoreModule:
    info: PackageMetadata
    pypi_name: str
    ConfigEntry: type[IAstrbotConfigEntry[AstrbotCoreConfig]]

    paths: IAstrbotPaths
    database: IAstrbotDatabase

    # region 基本生命周期
    @classmethod
    @moduleimpl(tryfirst=True)
    def Awake(
        cls,
    ) -> None:
        logger.info(f"{cls.info.get('name')} is awakening")

    # 开始自检 -- 尝试从入口点发现loader模块和frontend模块
    @classmethod
    @moduleimpl
    def Start(cls) -> None:
        logger.info(f"{cls.info.get('name')} start.")

        ...

    @classmethod
    @moduleimpl
    def OnDestroy(cls) -> None:
        logger.info("destroyed.")

    # endregion

    # region
    @classmethod
    def order_module(cls): ...
