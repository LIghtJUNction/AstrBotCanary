
#endregion
from __future__ import annotations
from collections.abc import AsyncIterable
from logging import LogRecord
from pathlib import Path

from typing import Any, Generic, Protocol, TypeVar, runtime_checkable, ContextManager, AsyncContextManager

from pluggy import HookimplMarker, HookspecMarker
from pydantic import BaseModel

from sqlalchemy import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from taskiq import AsyncBroker, AsyncResultBackend

from astrbot_canary_api.enums import AstrbotModuleType

type BROKER_TYPE = AsyncBroker
type RESULT_BACKEND_TYPE = AsyncResultBackend[BaseModel]
__all__ = [
    "IAstrbotPaths",
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

# 此协议用于type hint
# 模块实现应该按照ModuleSpec写
class IAstrbotModule(Protocol):
    module_type: AstrbotModuleType
    pypi_name: str
    """ 唯一，即项目名，例如：astrbot_canary """
    name: str
    """ 唯一，即入口点名，例如：canary_core """
    
    @classmethod
    def Awake(cls) -> None:
        ...
    @classmethod
    def Start(cls) -> None:
        ...
    @classmethod
    def OnDestroy(cls) -> None:
        ...

class AstrbotModuleSpec:
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
    cfg_file: Path | None

    @classmethod
    def bind(cls: type[IAstrbotConfigEntry[T]], group: str, name: str, default: T, description: str, cfg_dir: Path) -> IAstrbotConfigEntry[T]:
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
    async_engine: AsyncEngine | None
    AsyncSessionLocal: async_sessionmaker[AsyncSession] | None
    base: type[DeclarativeBase]  # declarative_base()
    """ SQLAlchemy declarative_base 对象，包含所有模型的基类 """

    @classmethod
    def connect(cls, db_path: Path) -> IAstrbotDatabase:
        """连接数据库，返回数据库实例"""
        ...

    @classmethod
    def init_base(cls, db_path: Path, base: type[DeclarativeBase]) -> IAstrbotDatabase:
        """初始化数据库表结构
        db_path: Path - 数据库文件路径
        base: SQLAlchemy DeclarativeBase 基类
            其子类将初始化
            自动映射为数据库表

        """
        ...

    def bind_base(self: IAstrbotDatabase, base: type[DeclarativeBase]) -> None:
        """实例化后绑定Base（DeclarativeBase），用于动态绑定模型基类。"""
        ...

    def execute(self, query: str, params: dict[str, Any] | tuple[Any, ...] | None = None) -> Any:
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

#region 日志处理器
class IAstrbotLogHandler(Protocol):
    """ 前端的控制台使用 """

    def emit(self, record: LogRecord) -> None:
        """处理并记录日志"""
        ...
    async def event_stream(self) -> AsyncIterable[str]:
        """异步日志流生成器，用于 SSE 推送"""
        while True:
            yield "data: ...\n\n"
        ...

    async def get_log_history(self) -> LogHistoryResponseData:
        """获取所有历史日志"""
        ...


#endregion

#region Taskiq!
"""AstrbotTaskiq!
封装接口
"""









#                          (
#                           )     (
#                    ___...(-------)-....___
#                .-""       )    (          ""-.
#          .-'``'|-._             )         _.-|
#         /  .--.|   `""---...........---""`   |
#        /  /    |                             |
#        |  |    |                             |
#         \  \   |                             |
#          `\ `\ |                             |
#            `\ `|                             |
#            _/ /\                             /
#           (__/  \                           /
#        _..---""` \                         /`""---.._
#     .-'           \                       /          '-.
#    :               `-.__             __.-'              :
#    :                  ) ""---...---"" (                 :
#     '._               `"--...___...--"`              _.'
#       \""--..__                              __..--""/
#        '._     """----.....______.....----"""     _.'
#           `""--..,,_____            _____,,..--""`
#                         `"""----"""`
# 








#region 主路由
class IAstrbotNetwork(Protocol):
    """ Astrbot Taskiq API: 仿FastAPI风格的taskiq封装
    负责路由分发、中间件管理、异常处理和文档生成
    """
    scheme: str = "astrbot"
    broker: BROKER_TYPE

    def __init__(
            self, 
            lifespan: AsyncContextManager[Any] | None = None,
        ) -> None:
        """包含自己的子路由和路由"""
        ...

    def add_middleware(self, middleware: Any) -> None:
        """添加中间件"""
        ...

    def get(self, path: str):
        """GET请求装饰器"""
        ...

    def post(self, path: str):
        """POST请求装饰器"""
        ...

    def put(self, path: str):
        """PUT请求装饰器"""
        ...
    
    def delete(self, path: str):
        """DELETE请求装饰器"""
        ...

    def head(self, path: str):
        """HEAD请求装饰器"""
        ...

    def options(self, path: str):
        """OPTIONS请求装饰器"""
        ...

    def patch(self, path: str):
        """PATCH请求装饰器"""
        ...

    def api_route(self, path: str, methods: list[str]) -> Any:
        """通用路由装饰器，接受所有HTTP方法"""
        ...

    def include_router(self, router: IAstrbotNetwork, prefix: str = "") -> None:
        """嵌套/挂载子路由，prefix为可选子路由前缀"""
        ...

    def get_routes(self) -> list[tuple[list[str], str, Any]]:
        """获取所有注册的路由 (方法列表, 完整路径, handler)"""
        ...

    def exception_handler(self, exc_type: type[BaseException]):
        """注册全局异常处理器，仿FastAPI"""
        ...

    def add_event_handler(self, event_type: str, handler: Any) -> None:
        """注册生命周期事件（startup/shutdown等）"""
        ...

    def normalize_path(self, path: str) -> str:
        """规范化路径，去除多余斜杠"""
        ...


#region 路由匹配器
class IRouteMatcher(Protocol):
    """
    路由匹配器接口
    支持路由查找、参数提取、反向查找等能力
    """
    def match(self, method: str, path: str) -> tuple[Any, dict[str, Any]] | None:
        """
        路由查找：根据方法和路径查找handler及参数
        返回: (handler, 路径参数字典) 或 None
        """
        ...

    def url_for(self, name: str, **path_params: dict[str, Any]) -> str:
        """
        反向查找：根据路由名和参数生成完整URL
        """
        ...

    def add_route(self, method: str, path: str, handler: Any, name: str | None = None) -> None:
        """
        注册路由
        """
        ...

    def get_routes(self) -> list[tuple[str, str, Any, str | None]]:
        """
        获取所有路由 (方法, 路径, handler, 路由名)
        """
        ...
#endregion

