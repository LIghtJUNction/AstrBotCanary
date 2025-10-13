from __future__ import annotations
from pathlib import Path
from types import TracebackType
from typing import Any, Protocol, runtime_checkable, ClassVar

from dependency_injector.providers import Container
from sqlalchemy.orm import Session
from astrbot_canary_api.enums import AstrBotModuleType


#region Interfaces

#region Module
@runtime_checkable
class IAstrbotModule(Protocol):
    """Interface for Astrbot modules."""
    name: ClassVar[str]
    pypi_name: ClassVar[str]
    module_type: ClassVar[AstrBotModuleType]
    version: ClassVar[str]
    authors: ClassVar[list[str]]
    description: ClassVar[str]
    enabled: bool

    def Awake(self, deps: Container[Any] | None = None ) -> None:
        """Called when the module is loaded."""
        ...
    def Start(self) -> None:
        """Called when the module is started."""
        ...
    def OnDestroy(self) -> None:
        """Called when the module is unloaded."""
        ...


@runtime_checkable
class IAstrbotLoaderModule(IAstrbotModule, Protocol):
    """Interface for Astrbot loader modules."""
    api_version: ClassVar[str]

    def Load(self, name: str) -> None:
        ...
    def Unload(self, name: str) -> None:
        ...
    def Reload(self, name: str) -> None:
        ...

@runtime_checkable
class IAstrbotUIModule(IAstrbotModule, Protocol):
    """Interface for Astrbot UI modules."""
    ...

#endregion

#region Paths

@runtime_checkable
class IAstrbotPaths(Protocol):
    """Interface for Astrbot path management."""

    astrbot_root: Path
    pypi_name: str
    
    @classmethod
    def root(cls, pypi_name: str) -> IAstrbotPaths:
        """ 返回模块路径根实例，用于访问模块的各类目录 """
        ...

    @property
    def config(self) -> Path:
        """ 返回模块配置目录 """
        ...

    @property
    def log(self) -> Path:
        """ 返回模块日志目录 """
        ...


#endregion
#region Config
@runtime_checkable
class IAstrbotConfigEntry(Protocol):
    """Interface for a single configuration entry."""
    pypi_name: str
    name: str
    group: str
    value: Any
    default: Any
    description: str

    @classmethod
    def bind(cls, pypi_name: str, group: str, name: str, default: Any, description: str , config_dir: Path) -> 'IAstrbotConfigEntry':
        """ 建议设置value时先从本地文件读取，不要直接使用默认值 """
        ...

    def load(self, pypi_name: str , config_dir: Path) -> None:
        """从本地文件加载配置"""
        ...

    def save(self , config_dir: Path) -> None:
        """将配置保存回本地文件"""
        ...

    def reset(self, config_dir: Path) -> None:
        """重置配置为默认值并保存"""
        ...


@runtime_checkable
class IAstrbotConfig(Protocol):
    """Interface for Astrbot configuration management."""
    _pypi_name: str
    configs: dict[str, dict[str, IAstrbotConfigEntry]]

    @classmethod
    def getConfig(cls, pypi_name: str) -> 'IAstrbotConfig':
        """获取自己的配置实例并注册到全局配置字典中"""
        ...

    def findEntry(self, group: str, name: str) -> IAstrbotConfigEntry | None:
        """找到指定组和名称的配置项，找不到返回None"""
        ...

    def bindEntry(self, entry: IAstrbotConfigEntry) -> IAstrbotConfigEntry:
        """绑定一个配置项"""
        ...



#endregion

#region database

@runtime_checkable
class IAstrbotDatabase(Protocol):
    """Interface for Astrbot database management, optimized for SQLAlchemy ORM."""
    database_url: str
    engine: Any  # sqlalchemy.engine.Engine
    session: Session | None  # sqlalchemy.orm.Session

    @classmethod
    def connect(cls, db_path: Path) -> 'IAstrbotDatabase':
        """连接数据库，返回数据库实例"""
        ...

    @classmethod
    def init_db(cls, db_path: Path, base: Any) -> None:
        """初始化数据库表结构"""
        ...

    def execute(self, query: str, params: Any = ()) -> Any:
        """执行原生SQL或ORM查询"""
        ...

    def close(self) -> None:
        """关闭数据库连接和会话"""
        ...

    def get_session(self) -> Session:
        """获取当前SQLAlchemy会话对象"""
        ...

    def transaction(self) -> Any:
        """上下文管理器/装饰器：自动提交/回滚事务
        用法：
        @db.transaction()
        def do_something(session): ...
        或 with db.transaction() as session: ...
        """
        ...

    def __enter__(self) -> 'IAstrbotDatabase':
        ...
    def __exit__(self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        ...
    async def __aenter__(self) -> 'IAstrbotDatabase':
        ...
    async def __aexit__(self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        ...


#endregion


#endregion