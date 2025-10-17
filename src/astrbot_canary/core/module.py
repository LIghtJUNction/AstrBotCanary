"""
astrbot_canary 核心模块
注意：不要在本模块内写异步函数
异步循环只能在最后一个启动的模块内编写

比如web模块
请务必使用await broker.startup()等待broker启动完成

"""
from astrbot_canary_api.decorators import AstrbotModule
from astrbot_canary_api import (
    moduleimpl,
)
"""
依赖抽象，而非具体
"""
from importlib.metadata import PackageMetadata

"""
稳定第三方库直接依赖
"""
from logging import getLogger

logger = getLogger("astrbot_canary.module.core")

@AstrbotModule(pypi_name="astrbot_canary")
class AstrbotCoreModule():
    # cls.info : PackageMetadata
    info: PackageMetadata
#region 基本生命周期

    @classmethod
    @moduleimpl
    def Awake(
        cls,
    ) -> None:
        logger.info(f"{cls.info}")

    # 开始自检 -- 尝试从入口点发现loader模块和frontend模块
    @classmethod
    @moduleimpl
    def Start(cls) -> None:

        logger.info(f"started.")

        ...
    @classmethod
    @moduleimpl
    def OnDestroy(cls) -> None:
        logger.info(f"destroyed.")


#endregion

