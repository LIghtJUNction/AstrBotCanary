from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager, AbstractContextManager
    from pathlib import Path

class IAstrbotConfigEntry[T: BaseModel](ABC):
    """配置条目的抽象基类."""

    @classmethod
    @abstractmethod
    def bind(
        cls: type[IAstrbotConfigEntry[T]],
        group: str,
        name: str,
        default: T,
        description: str,
        cfg_dir: Path,
    ) -> IAstrbotConfigEntry[T]:
        """工厂方法:优先从文件加载,否则新建并保存.自动根据default类型推断模型类型."""

    @abstractmethod
    def save(self) -> None:
        """保存配置到 toml 文件(只用BaseModel标准序列化,Path等类型转为字符串)."""

    @abstractmethod
    def load(self) -> None:
        """从本地文件加载配置(覆盖当前值,只用BaseModel标准反序列化)."""

    @abstractmethod
    def reset(self) -> None:
        """重置为默认值并保存."""

    @abstractmethod
    def __repr__(self) -> str:
        """REPR."""

    @abstractmethod
    def __str__(self) -> str:
        """STR."""


class IAstrbotPaths(ABC):
    """路径管理的抽象基类."""

    @abstractmethod
    def __init__(self, name: str) -> None:
        """初始化路径管理器."""

    @classmethod
    @abstractmethod
    def getPaths(cls, name: str) -> IAstrbotPaths:
        """返回Paths实例,用于访问模块的各类目录."""

    @property
    @abstractmethod
    def root(self) -> Path:
        """获取根目录."""

    @property
    @abstractmethod
    def home(self) -> Path:
        """获取模块/插件主目录."""

    @property
    @abstractmethod
    def config(self) -> Path:
        """获取模块配置目录."""

    @property
    @abstractmethod
    def data(self) -> Path:
        """获取模块数据目录."""

    @property
    @abstractmethod
    def log(self) -> Path:
        """获取模块日志目录."""

    @abstractmethod
    def reload(self) -> None:
        """重新加载环境变量."""

    @abstractmethod
    def chdir(self, cwd: str = "home") -> AbstractContextManager[Path]:
        """临时切换到指定目录, 子进程将继承此 CWD。"""

    @abstractmethod
    async def achdir(self, cwd: str = "home") -> AbstractAsyncContextManager[Path]:
        """异步临时切换到指定目录, 子进程将继承此 CWD。"""

