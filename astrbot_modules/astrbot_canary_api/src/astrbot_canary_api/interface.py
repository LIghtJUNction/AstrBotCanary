from __future__ import annotations
from pathlib import Path

from typing import Any, Generic, Protocol, TypeVar, runtime_checkable, ContextManager, AsyncContextManager

from pluggy import HookimplMarker, HookspecMarker
from pydantic import BaseModel

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from taskiq import AsyncBroker, AsyncResultBackend

type BROKER_TYPE = AsyncBroker
type RESULT_BACKEND_TYPE = AsyncResultBackend[BaseModel]
__all__ = [
    "IAstrbotPaths",
    "IAstrbotConfig",
    "IAstrbotDatabase",
    "BROKER_TYPE",
    "RESULT_BACKEND_TYPE",
    "ASTRBOT_MODULES_HOOK_NAME",
    "modulespec",
    "moduleimpl"
]

#region Interfaces

#region Module
# ---------------------------------------------------------------------------
# Pluggy hookspecs for modules
# ---------------------------------------------------------------------------
ASTRBOT_MODULES_HOOK_NAME = "astrbot.modules"  # Must match the name used in PluginManager
# Hook markers - plugins must use the same project name for @hookimpl
modulespec = HookspecMarker(ASTRBOT_MODULES_HOOK_NAME)
moduleimpl = HookimplMarker(ASTRBOT_MODULES_HOOK_NAME)

class ModuleSpec:
    """Astrbot 模块规范
    Awake: 自身初始化时调用，请勿编写涉及除本模块之外的逻辑
        建议操作：
            绑定配置
            配置数据库
            ...
    Start: 模块启动时调用，负责启动模块的主要功能，可以涉及与其它模块交互
    OnDestroy: 模块卸载时调用，负责清理资源和保存状态
        建议操作：
            关闭数据库连接
            停止后台任务
            保存配置
            释放资源
            ！无需使用@atexit注册退出钩子，模块框架会统一调用 OnDestroy

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

#endregion

#region Paths
@runtime_checkable
class IAstrbotPaths(Protocol):
    """Interface for Astrbot path management."""

    astrbot_root: Path
    def __init__(self,pypi_name: str) -> None:
        ...
    
    @classmethod
    def getPaths(cls, pypi_name: str) -> IAstrbotPaths:
        """ 返回模块路径根实例，用于访问模块的各类目录 """
        ...

    @property
    def config(self) -> Path:
        """ 返回模块配置目录 """
        ...

    @property
    def data(self) -> Path:
        """ 返回模块数据目录 """
        ...

    @property
    def log(self) -> Path:
        """ 返回模块日志目录 """
        ...

#endregion
#region Config
T = TypeVar("T", bound=BaseModel)

class IAstrbotConfigEntry(Protocol, Generic[T]):
    """单个配置项的协议（作为 IAstrbotConfig 的内部类）"""
    name: str
    group: str
    value: T
    default: T
    description: str
    _cfg_file: Path | None
    @classmethod
    def bind(cls, group: str, name: str, default: T, description: str, cfg_dir: Path) -> IAstrbotConfigEntry[T]:
        """按 group 保存到 {cfg_dir}/{group}.toml，并返回绑定好的条目实例。"""
        ...
    def load(self) -> None:
        """从所在组文件加载本项数据（不影响同组其它项）。"""
        ...
    def save(self) -> None:
        """将本项合并到所在组文件并保存（不覆盖同组其它项）。"""
        ...
    def reset(self) -> None:
        """重置为默认值并保存。"""
        ...
        

@runtime_checkable
class IAstrbotConfig(Protocol):
    """按实例管理模块配置（与 core.config.AstrbotConfig 保持一致）。
    将配置项定义为 IAstrbotConfig.Entry 的嵌套协议，以匹配 AstrbotConfig.Entry 的实现方式。
    """
    Entry = IAstrbotConfigEntry
    # 实现可以提供这个便捷引用

    @classmethod
    def getConfig(cls) -> IAstrbotConfig:
        """返回一个新的配置实例"""
        ...

    def findEntry(self, group: str, name: str) -> IAstrbotConfigEntry[Any] | None:
        """在本实例作用域查找配置项，找不到返回 None。"""
        ...

    def bindEntry(self, entry: IAstrbotConfigEntry[Any]) -> IAstrbotConfigEntry[Any]:
        """绑定（或覆盖）一个配置项到本实例。"""
        ...

#endregion

#region database

"""Transaction context aliases to match contextmanager/asynccontextmanager return types."""
TransactionContext = ContextManager[Session]
AsyncTransactionContext = AsyncContextManager[AsyncSession]

@runtime_checkable
class IAstrbotDatabase(Protocol):
    """Interface for Astrbot database management, optimized for SQLAlchemy ORM."""
    db_path: Path
    """ 数据库文件路径 """
    database_url: str
    """ 数据库连接URL """
    engine: Engine | None  # sqlalchemy.engine.Engine
    """ SQLAlchemy引擎实例 """
    # session: 不再在接口上保持单一 Session 实例，使用 SessionLocal factory
    SessionLocal: sessionmaker[Session] | None
    async_engine: Any | None
    AsyncSessionLocal: async_sessionmaker[AsyncSession] | None
    base: Any  # declarative_base()
    """ SQLAlchemy declarative_base 对象，包含所有模型的基类 """

    @classmethod
    def connect(cls, db_path: Path) -> IAstrbotDatabase:
        """连接数据库，返回数据库实例"""
        ...

    @classmethod
    def init_db(cls, db_path: Path, base: Any) -> IAstrbotDatabase:
        """初始化数据库表结构
        db_path: Path - 数据库文件路径
        base: SQLAlchemy declarative_base 对象，包含所有模型的基类

        """
        ...

    def execute(self, query: str, params: Any = ()) -> Any:
        """执行原生SQL或ORM查询"""
        ...

    def close(self) -> None:
        """关闭数据库连接和会话"""
        ...

    async def aclose(self) -> None:
        """异步释放异步引擎/会话资源（若有）。"""
        ...

    def transaction(self) -> TransactionContext:
        """上下文管理器：自动提交/回滚事务
        用法：
        @db.transaction()
        def do_something(session): ...
        或 with db.transaction() as session: ...
        """
        ...

    def atransaction(self) -> AsyncTransactionContext:
        """异步上下文管理器：自动提交/回滚事务
        用法：
        async with db.atransaction() as session: ...
        """
        ...

    def session_scope(self) -> TransactionContext:
        """显式的同步 session 上下文管理器（短生命周期 session）。"""
        ...

    async def __aenter__(self) -> IAstrbotDatabase:
        """异步上下文管理器入口（如果实现）。"""
        ...

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """异步上下文管理器出口（如果实现）。"""
        ...

    def __enter__(self) -> IAstrbotDatabase:
        """同步上下文管理器入口（如果实现）。"""
        ...

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """同步上下文管理器出口（如果实现）。"""
        ...

#endregion
#endregion