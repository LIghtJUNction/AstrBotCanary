# endregion
from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Protocol,
)

from pluggy import HookimplMarker, HookspecMarker

if TYPE_CHECKING:
    from collections.abc import AsyncIterable
    from logging import LogRecord

    from astrbot_canary_api.models import LogHistoryResponseData


__all__ = [
    "ASTRBOT_MODULES_HOOK_NAME",
    "moduleimpl",
    "modulespec",
]

# region Interfaces

# region Module
# ---------------------------------------------------------------------------
# Pluggy hookspecs for modules
# ---------------------------------------------------------------------------
ASTRBOT_MODULES_HOOK_NAME = (
    "astrbot.modules"  # Must match the name used in PluginManager
)
# Hook markers - plugins must use the same project name for @hookimpl
modulespec = HookspecMarker(ASTRBOT_MODULES_HOOK_NAME)
moduleimpl = HookimplMarker(ASTRBOT_MODULES_HOOK_NAME)

# 此协议用于type hint
# 模块实现应该按照ModuleSpec写



class AstrbotModuleSpec:
    """Astrbot 模块规范
    Awake: 自身初始化时调用,请勿编写涉及除本模块之外的逻辑
        建议操作:
            绑定配置
            配置数据库
            ...
    Start: 模块启动时调用,负责启动模块的主要功能,可以涉及与其它模块交互
    OnDestroy: 模块卸载时调用,负责清理资源和保存状态
        建议操作:
            关闭数据库连接
            停止后台任务
            保存配置
            释放资源
            !无需使用@atexit注册退出钩子,模块框架会统一调用 OnDestroy.

    """

    @classmethod
    @modulespec
    def Awake(cls) -> None:
        """Called when the module is loaded."""

    @classmethod
    @modulespec
    def Start(cls) -> None:
        """Called when the module is started."""

    @classmethod
    @modulespec
    def OnDestroy(cls) -> None:
        """Called when the module is unloaded."""


# endregion

# region 日志处理器
class IAstrbotLogHandler(Protocol):
    """前端的控制台使用."""

    def emit(self, record: LogRecord) -> None:
        """处理并记录日志."""
        ...

    async def event_stream(self) -> AsyncIterable[str]:
        """异步日志流生成器,用于 SSE 推送."""
        while True:
            yield "data: ...\n\n"
        ...

    async def get_log_history(self) -> LogHistoryResponseData:
        """获取所有历史日志."""
        ...


# endregion
