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
from typing import Any

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
    @moduleimpl
    def Awake(
        self,
    ) -> None:
        logger.info(f"{self.info.get('Name')} v{self.info.get('Version')} is awakening.")

    # 开始自检 -- 尝试从入口点发现loader模块和frontend模块
    @moduleimpl
    def Start(self) -> None:

        logger.info(f"{self.info.get('Name')} v{self.info.get('Version')} has started.")

        ...

    @moduleimpl
    def OnDestroy(self) -> None:
        logger.info(f"{self.info.get('Name')} v{self.info.get('Version')} is being destroyed.")

#region 特有功能函数
    @staticmethod
    def setActive(active: bool, module: Any) -> None:
        """Enable or disable the module at runtime."""
        if module.enabled == active:
            logger.info(f"{module.name} is already {'enabled' if active else 'disabled'}. No action taken.")
            return
        module.enabled = active
        state = "enabled" if active else "disabled"
        logger.info(f"{module.name} has been {state} at runtime.")
        if not active:
            module.OnDestroy()
        if active:
            module.Start()

#endregion
#endregion

