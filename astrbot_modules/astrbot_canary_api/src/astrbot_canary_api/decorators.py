"""Q&A.

AstrbotModule 装饰器为什么需要
pypi_name / name两个参数?并且两者都要唯一性?
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from taskiq import AsyncBroker

if TYPE_CHECKING:
    from collections.abc import Callable
from importlib.metadata import (
    Distribution,
    PackageMetadata,
    PackageNotFoundError,
    distribution,
)
from inspect import signature
from logging import Logger, getLogger
from typing import ClassVar, ParamSpec, TypeVar, overload

from packaging.utils import canonicalize_name

if TYPE_CHECKING:
    from pydantic import BaseModel

from astrbot_canary_api import (
    AstrbotModuleType,
    IAstrbotDatabase,
    IAstrbotPaths,
)
from astrbot_canary_api.interface import IAstrbotConfigEntry, IAstrbotModule

IAstrbotModule_ref = IAstrbotModule

logger: Logger = getLogger("astrbot.module.api")


P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")


class AstrbotInjector:
    """Astrbot依赖注入器..

    推荐用法:@AstrbotInjector.decorator
    支持全局依赖注入,类型安全

    例子:
        @AstrbotInjector
        def my_function(
            db: IAstrbotDatabase,
            config: IAstrbotConfigEntry[MyConfig],
        ) -> None:
            ...

        # 注入依赖
        AstrbotInjector.set("db", my_database_instance)
        AstrbotInjector.set("config", my_config_entry_instance)

        # 调用函数时会自动注入依赖
        my_function()  # db 和 config 会被自动传入

    不保留签名,直接装饰
        保留签名:使用get方法获取依赖
        再写一个函数式装饰器我认为没必要
    """

    global_dependencies: ClassVar[dict[str, Any]] = {}
    local_injector: ClassVar[dict[str, AstrbotInjector]] = {}

    func: Callable[..., Any] | None
    name: str | None

    @overload
    def __init__(self, arg: Callable[..., Any]) -> None: ...
    @overload
    def __init__(self, arg: str) -> None: ...

    def __init__(self, arg: Callable[..., Any] | str) -> None:
        """初始化依赖注入器."""
        self.local_dependencies: dict[str, Any] = {}
        if callable(arg):
            self.func = arg
            self.name = None
        else:
            self.name = arg
            self.func = None

    def __call__(self, *args: object, **kwargs: object) -> object:
        """调用依赖注入器,自动注入依赖并执行目标函数."""

        def inject_dependencies(
            func: Callable[..., Any],
            call_args: tuple[Any, ...],
            call_kwargs: dict[str, Any],
        ) -> object:
            sig = signature(func)
            # 注入局部依赖优先,然后全局
            for name, dep in self.local_dependencies.items():
                if name in sig.parameters and name not in call_kwargs:
                    call_kwargs[name] = dep
            for name, dep in AstrbotInjector.global_dependencies.items():
                if name in sig.parameters and name not in call_kwargs:
                    call_kwargs[name] = dep
            return func(*call_args, **call_kwargs)

        if self.func is None:

            def wrapper(*a: object, **kw: object) -> object:
                if not a or not callable(a[0]):
                    mag = "Decorator must be used with a callable."
                    raise TypeError(mag)
                func = a[0]
                return inject_dependencies(func, a, kw)

            return wrapper

        return inject_dependencies(self.func, args, kwargs)

    @classmethod
    def set(cls, name: str, value: type) -> None:
        """设置全局依赖项."""
        cls.global_dependencies[name] = value

    @classmethod
    def get(cls, name: str) -> type:
        """获取全局依赖项."""
        return cls.global_dependencies.get(name)

    @classmethod
    def remove(cls, name: str) -> None:
        """移除全局依赖项."""
        cls.global_dependencies.pop(name, None)

    @classmethod
    def getInjector(cls, injector_name: str) -> AstrbotInjector:
        """获取或创建指定名称的局部依赖注入器."""
        if injector_name not in cls.local_injector:
            cls.local_injector[injector_name] = AstrbotInjector(injector_name)
        return cls.local_injector[injector_name]

    # 局部依赖注入器
    def set_local(self, name: str, value: object) -> None:
        """设置局部依赖项."""
        self.local_dependencies[name] = value

    def get_local(self, name: str) -> object:
        """获取局部依赖项."""
        return self.local_dependencies.get(name)

    def remove_local(self, name: str) -> None:
        """移除局部依赖项."""
        self.local_dependencies.pop(name, None)


class AstrbotModuleMeta(type):
    """用于设置AstrbotModule的类属性."""

    _modules_registry: ClassVar[dict[str, type]] = {}
    _paths_impl: ClassVar[type[IAstrbotPaths] | None] = None
    _config_entry_impl: ClassVar[type[IAstrbotConfigEntry[BaseModel]] | None] = None
    _database_impl: ClassVar[type[IAstrbotDatabase] | None] = None
    _broker_impl: ClassVar[AsyncBroker | None] = None

    # 单一实例
    _paths: ClassVar[IAstrbotPaths | None] = None
    _config_entry: ClassVar[IAstrbotConfigEntry[BaseModel] | None] = None
    _database: ClassVar[IAstrbotDatabase | None] = None

    # 其他元数据
    _pypi_name: str
    _name: str
    _module_type: AstrbotModuleType
    _info: PackageMetadata | None = None

    def __new__(
        mcs: type[AstrbotModuleMeta],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, object],
    ) -> type:
        """创建 AstrbotModuleMeta 的新实例."""
        # 检测类名冲突
        if name in mcs._modules_registry:
            msg = f"模块冲突: {name}"
            raise ValueError(msg)
        # 保留原始bases,避免元类冲突

        # 初始化所有ClassVar属性
        if not hasattr(mcs, "_paths_impl"):
            mcs._paths_impl = None
        if not hasattr(mcs, "_config_entry_impl"):
            mcs._config_entry_impl = None
        if not hasattr(mcs, "_database_impl"):
            mcs._database_impl = None
        if not hasattr(mcs, "_broker_impl"):
            mcs._broker_impl = None
        if not hasattr(mcs, "_paths"):
            mcs._paths = None
        if not hasattr(mcs, "_config_entry"):
            mcs._config_entry = None
        if not hasattr(mcs, "_database"):
            mcs._database = None

        cls = super().__new__(mcs, name, bases, namespace)
        mcs._modules_registry[name] = cls

        # 检测是否实现了必要接口
        # 只允许 runtime_checkable 协议用于 isinstance 检查
        # 跳过issubclass检查,避免mypy报错
        return cls

    def __init__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, object],
    ) -> None:
        super().__init__(name, bases, namespace)

    @property
    def Paths(cls) -> type[IAstrbotPaths]:
        """获取 AstrbotPaths 的实现类."""
        impl = AstrbotModuleMeta._paths_impl
        if impl is None:
            Paths_impl = AstrbotInjector.get("AstrbotPaths")
            # 只允许类型对象赋值
            if isinstance(Paths_impl, type):
                AstrbotModuleMeta._paths_impl = Paths_impl
                impl = Paths_impl
            else:
                msg = (
                    "AstrbotPaths 未注入或类型不正确,请在启动时设置 "
                    "AstrbotInjector.set('AstrbotPaths', <实现类>)"
                )
                raise RuntimeError(msg)
        return impl

    @Paths.setter
    def Paths(cls, value: type[IAstrbotPaths]) -> None:
        """设置 AstrbotPaths 的实现类."""
        AstrbotModuleMeta._paths_impl = value

    @property
    def ConfigEntry(cls) -> type[IAstrbotConfigEntry[BaseModel]]:
        """获取 AstrbotConfigEntry 的实现类."""
        impl = AstrbotModuleMeta._config_entry_impl
        if impl is None:
            ConfigEntry_impl = AstrbotInjector.get("AstrbotConfigEntry")
            if isinstance(ConfigEntry_impl, type):
                AstrbotModuleMeta._config_entry_impl = ConfigEntry_impl
                impl = ConfigEntry_impl
            else:
                msg = (
                    "AstrbotConfigEntry 未注入或类型不正确,请在启动时设置 "
                    "AstrbotInjector.set('AstrbotConfigEntry', <实现类>)"
                )
                raise RuntimeError(msg)
        return impl

    @ConfigEntry.setter
    def ConfigEntry(cls, value: type[IAstrbotConfigEntry[BaseModel]]) -> None:
        """设置 AstrbotConfigEntry 的实现类."""
        AstrbotModuleMeta._config_entry_impl = value

    @property
    def Database(cls) -> type[IAstrbotDatabase]:
        """获取 AstrbotDatabase 的实现类."""
        impl = AstrbotModuleMeta._database_impl
        if impl is None:
            Database_impl = AstrbotInjector.get("AstrbotDatabase")
            if isinstance(Database_impl, type):
                AstrbotModuleMeta._database_impl = Database_impl
                impl = Database_impl
            else:
                msg = (
                    "AstrbotDatabase 未注入或类型不正确,请在启动时设置 "
                    "AstrbotInjector.set('AstrbotDatabase', <实现类>)"
                )
                raise RuntimeError(msg)
        return impl

    @Database.setter
    def Database(cls, value: type[IAstrbotDatabase]) -> None:
        """设置 AstrbotDatabase 的实现类."""
        AstrbotModuleMeta._database_impl = value

    # 实例

    @property
    def broker(cls) -> AsyncBroker:
        """获取 AsyncBroker 的实现实例.."""
        impl = AstrbotModuleMeta._broker_impl
        if impl is None:
            broker_impl = AstrbotInjector.get("broker")
            if broker_impl is not None and isinstance(broker_impl, AsyncBroker):
                AstrbotModuleMeta._broker_impl = broker_impl
                impl = broker_impl
            else:
                msg = (
                    "AsyncBroker 未注入或类型不正确,请在启动时设置 "
                    "AstrbotInjector.set('broker', <全局单例>)"
                )
                raise RuntimeError(msg)
        return impl

    @broker.setter
    def broker(cls, value: AsyncBroker) -> None:
        """设置 AsyncBroker 的实现实例.."""
        AstrbotModuleMeta._broker_impl = value

    @property
    def paths(cls) -> IAstrbotPaths:
        if AstrbotModuleMeta._paths:
            return AstrbotModuleMeta._paths
        if cls.Paths is None:
            msg = "Paths 未设置"
            raise RuntimeError(msg)
        return cls.Paths.getPaths(cls.pypi_name)

    @paths.setter
    def paths(cls, value: IAstrbotPaths) -> None:
        AstrbotModuleMeta._paths = value

    @property
    def database(cls) -> IAstrbotDatabase:
        if AstrbotModuleMeta._database:
            return AstrbotModuleMeta._database
        if cls.Database is None:
            msg = "Database 未设置"
            raise RuntimeError(msg)
        return cls.Database.connect(cls.paths.data / f"{cls.pypi_name}.db")

    @database.setter
    def database(cls, value: IAstrbotDatabase) -> None:
        AstrbotModuleMeta._database = value

    # 其他属性
    @property
    def pypi_name(cls) -> str:
        return cls._pypi_name

    @pypi_name.setter
    def pypi_name(cls, value: str) -> None:
        # 检查是否是合法的PyPI包名
        value = canonicalize_name(value)  # 标准化名称
        cls._pypi_name = value

    @property
    def name(cls) -> str:
        return cls._name

    @name.setter
    def name(cls, value: str) -> None:
        cls._name = value
        logger.debug("注册:%s(%s)", cls._name, cls.pypi_name)

    @property
    def module_type(cls) -> AstrbotModuleType:
        return cls._module_type

    @module_type.setter
    def module_type(cls, value: str | AstrbotModuleType) -> None:
        if isinstance(value, str):
            try:
                value = AstrbotModuleType[value.upper()]
            except KeyError:
                msg = f"未知的模块类型:{value}"
                raise ValueError(msg) from None

        cls._module_type = value

    @property
    def info(cls) -> PackageMetadata:
        if cls._info is None:
            try:
                dist: Distribution = distribution(cls.pypi_name)
                cls._info = dist.metadata
            except PackageNotFoundError:
                msg = f"未找到包:{cls.pypi_name},请确认包已安装且名称正确!"
                raise RuntimeError(msg) from None
        return cls._info

    @info.setter
    def info(cls, value: PackageMetadata) -> None:
        cls._info = value


class AstrbotModule:
    """装饰器类,用于标记模块并自动提取元数据,注入抽象接口的具体实现
    大写开头表示这是一个类
    小写开头表示这是一个实例
    注意:
        此类需要核心模块注入具体实现
    注入:
        核心模块负责注入具体实现.
    """

    def __init__(
        self,
        pypi_name: str,
        name: str,
        module_type: AstrbotModuleType,
        info: PackageMetadata | None = None,
    ) -> None:
        self.pypi_name: str = pypi_name
        self.name: str = name
        self.module_type: AstrbotModuleType = module_type
        self.info: PackageMetadata | None = info

    def __call__(
        self,
        cls: type,
    ) -> AstrbotModuleMeta:
        DecoratedClass = AstrbotModuleMeta(
            cls.__name__,
            (),
            dict(cls.__dict__),
        )
        DecoratedClass.pypi_name = self.pypi_name
        DecoratedClass.name = self.name
        DecoratedClass.module_type = self.module_type
        if self.info is not None:
            DecoratedClass.info = self.info

        return DecoratedClass
