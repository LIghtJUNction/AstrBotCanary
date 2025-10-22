# endregion
from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Protocol,
    Self,
    TypeVar,
    runtime_checkable,
)

from pluggy import HookimplMarker, HookspecMarker
from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import AsyncIterable
    from contextlib import (
        AbstractAsyncContextManager,
        AbstractContextManager,
    )
    from logging import LogRecord
    from pathlib import Path
    from types import TracebackType

    from sqlalchemy import Engine
    from sqlalchemy.ext.asyncio import (
        AsyncEngine,
        AsyncSession,
        async_sessionmaker,
    )
    from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
    from taskiq import AsyncBroker, AsyncResultBackend

    TransactionContext = AbstractContextManager["Session"]
    AsyncTransactionContext = AbstractAsyncContextManager["AsyncSession"]

type BROKER_TYPE = AsyncBroker
type RESULT_BACKEND_TYPE = AsyncResultBackend[BaseModel]


__all__ = [
    "ASTRBOT_MODULES_HOOK_NAME",
    "BROKER_TYPE",
    "RESULT_BACKEND_TYPE",
    "IAstrbotDatabase",
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

# region database



@runtime_checkable
class IAstrbotDatabase(Protocol):
    """Interface for Astrbot database management, optimized for SQLAlchemy ORM."""

    db_path: Path
    """ 数据库文件路径 """
    database_url: str
    """ 数据库连接URL """
    engine: Engine | None  # sqlalchemy.engine.Engine
    """ SQLAlchemy引擎实例 """
    # session: 不再在接口上保持单一 Session 实例,使用 SessionLocal factory
    SessionLocal: sessionmaker[Session] | None
    async_engine: AsyncEngine | None
    AsyncSessionLocal: async_sessionmaker[AsyncSession] | None
    base: type[DeclarativeBase]  # declarative_base()
    """ SQLAlchemy declarative_base 对象,包含所有模型的基类 """

    @classmethod
    def connect(cls, db_path: Path) -> IAstrbotDatabase:
        """连接数据库,返回数据库实例."""
        ...

    @classmethod
    def init_base(cls, db_path: Path, base: type[DeclarativeBase]) -> IAstrbotDatabase:
        """初始化数据库表结构
        db_path: Path - 数据库文件路径
        base: SQLAlchemy DeclarativeBase 基类
            其子类将初始化
            自动映射为数据库表.

        """
        ...

    def bind_base(self: IAstrbotDatabase, base: type[DeclarativeBase]) -> None:
        """实例化后绑定Base(DeclarativeBase),用于动态绑定模型基类.."""
        ...

    def execute(
        self,
        query: str,
        params: dict[str, object] | tuple[object, ...] | None = None,
    ) -> object:
        """执行原生SQL或ORM查询."""
        ...

    def close(self) -> None:
        """关闭数据库连接和会话."""
        ...

    async def aclose(self) -> None:
        """异步释放异步引擎/会话资源(若有).."""
        ...

    def transaction(self) -> TransactionContext:
        """上下文管理器:自动提交/回滚事务
        短生命周期
        用法:
        @db.transaction()
        def do_something(session): ...
        或 with db.transaction() as session: ...
        """
        ...

    def atransaction(self) -> AsyncTransactionContext:
        """异步上下文管理器:自动提交/回滚事务
        用法:
        async with db.atransaction() as session: ...
        """
        ...


    async def __aenter__(self) -> Self:
        """异步上下文管理器入口(如果实现).."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """异步上下文管理器出口(如果实现).."""
        ...

    def __enter__(self) -> Self:
        """同步上下文管理器入口(如果实现).."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """同步上下文管理器出口(如果实现).."""
        ...


# endregion
class LogHistoryItem(BaseModel):
    level: str
    time: str
    data: str


class LogSSEItem(BaseModel):
    type: str
    level: str
    time: str
    data: str


class LogHistoryResponseData(BaseModel):
    logs: list[LogHistoryItem]


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
