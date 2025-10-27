# endregion
from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Protocol,
    runtime_checkable,
)

from pluggy import HookimplMarker, HookspecMarker
from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import AsyncIterable
    from logging import LogRecord
    from pathlib import Path

    from astrbot_canary_api.enums import AstrbotModuleType
    from astrbot_canary_api.models import LogHistoryResponseData


__all__ = [
    "ASTRBOT_MODULES_HOOK_NAME",
    "IAstrbotPaths",
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


@runtime_checkable
class IAstrbotModule(Protocol):
    """Astrbot 模块接口协议
    请使用@AstrbotModule注入必要的元数据
    以及注入一些实用的类/实例
    本协议仅供检查/规范
    以及类型提示使用.
    """

    pypi_name: str
    name: str
    module_type: AstrbotModuleType

    @classmethod
    def Awake(cls) -> None:
        """模块自身初始化时调用."""
        ...

    @classmethod
    def Start(cls) -> None:
        """模块启动时调用."""
        ...

    @classmethod
    def OnDestroy(cls) -> None:
        """模块卸载时调用."""
        ...


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


# region Paths
@runtime_checkable
class IAstrbotPaths(Protocol):
    """Interface for Astrbot path management."""

    astrbot_root: Path
    pypi_name: str

    def __init__(self, pypi_name: str) -> None: ...

    @classmethod
    def getPaths(cls, pypi_name: str) -> IAstrbotPaths:
        """返回模块路径根实例,用于访问模块的各类目录."""
        ...

    @property
    def config(self) -> Path:
        """返回模块配置目录."""
        ...

    @property
    def data(self) -> Path:
        """返回模块数据目录."""
        ...

    @property
    def log(self) -> Path:
        """返回模块日志目录."""
        ...


# endregion
# region Config


@runtime_checkable
class IAstrbotConfigEntry[T: BaseModel](Protocol):
    """单个配置项的协议(作为 IAstrbotConfig 的内部类)."""

    name: str
    group: str
    value: T
    default: T
    description: str
    cfg_file: Path | None

    @classmethod
    def bind(
        cls: type[IAstrbotConfigEntry[T]],
        group: str,
        name: str,
        default: T,
        description: str,
        cfg_dir: Path,
    ) -> IAstrbotConfigEntry[T]:
        """按 group 保存到 {cfg_dir}/{group}.toml,并返回绑定好的条目实例.."""
        ...

    def load(self) -> None:
        """从所在组文件加载本项数据(不影响同组其它项).."""
        ...

    def save(self) -> None:
        """将本项合并到所在组文件并保存(不覆盖同组其它项).."""
        ...

    def reset(self) -> None:
        """重置为默认值并保存.."""
        ...


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
