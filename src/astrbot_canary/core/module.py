"""
astrbot_canary 核心模块
注意：不要在本模块内写异步函数
异步循环只能在最后一个启动的模块内编写

比如web模块
请务必使用await broker.startup()等待broker启动完成

"""
from pydantic import BaseModel
from astrbot_canary_api.decorators import AstrbotModule
from astrbot_canary_api import (
    IAstrbotConfig,
    IAstrbotPaths,
    moduleimpl,
)
from astrbot_canary_api.interface import IAstrbotConfigEntry
"""
依赖抽象，而非具体
"""
from importlib.metadata import PackageMetadata

"""
稳定第三方库直接依赖
"""
from logging import getLogger

logger = getLogger("astrbot_canary.module.core")

class AstrbotCoreConfig(BaseModel):
    """
    核心模块配置项
    """
    modules: list[str]
    """ 发现的模块 """
    boot: list[str]
    """ 启动Astrbot-模块启动顺序 """

@AstrbotModule(pypi_name="astrbot_canary")
class AstrbotCoreModule():
    info: PackageMetadata
#region 基本生命周期
    pypi_name: str
    Config: IAstrbotConfig
    ConfigEntry: IAstrbotConfigEntry[AstrbotCoreConfig]
    paths: IAstrbotPaths

    @classmethod
    @moduleimpl
    def Awake(
        cls,
    ) -> None:
        logger.info(f"{cls.info}")

        cls.cfg_core = cls.Config.bindEntry(
            entry=cls.ConfigEntry.bind(
                group="core",
                name="boot",
                default=AstrbotCoreConfig(
                    modules=["astrbot_canary_core", "astrbot_canary_loader", "astrbot_canary_web", "astrbot_canary_tui"],
                    boot=["astrbot_canary_core", "astrbot_canary_loader", "astrbot_canary_web"],
                ),
                description="核心模块配置项",
                cfg_dir=cls.paths.config,
            )
        )

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

