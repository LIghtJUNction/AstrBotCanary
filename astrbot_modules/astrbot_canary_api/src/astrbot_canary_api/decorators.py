""" Q&A
AstrbotModule 装饰器为什么需要
pypi_name / name两个参数？并且两者都要唯一性？

pypi_name用于标识模块来源
不是所有模块都必须上传至pypi,这个还可以填写git仓库链接
还可以填写wheel文件路径/项目路径...
即uv pip install pypi_name
pip install pypi_name
...

name（即入口点名称）将被写入配置方便下次快速启动


"""
from __future__ import annotations
from inspect import signature
from importlib.metadata import Distribution, PackageNotFoundError, distribution , PackageMetadata
from packaging.utils import canonicalize_name
from taskiq import AsyncBroker
from typing import Any, ParamSpec, TypeVar
from collections.abc import Callable

from astrbot_canary_api import (
    AstrbotModuleType, 
    IAstrbotDatabase, 
    IAstrbotPaths,
    IAstrbotConfigEntry
)
from astrbot_canary_api.interface import IAstrbotModule

from logging import getLogger , Logger
logger: Logger = getLogger("astrbot.module.api")


P = ParamSpec('P')
R = TypeVar('R')

class AstrbotInjector:
    """
    Astrbot依赖注入器
    推荐用法：@AstrbotInjector.decorator
    支持全局依赖注入，类型安全
    例子：
        @AstrbotInjector
        def my_function(db: IAstrbotDatabase, config: IAstrbotConfigEntry[MyConfig]) -> None:
            ...

        # 注入依赖
        AstrbotInjector.set("db", my_database_instance)
        AstrbotInjector.set("config", my_config_entry_instance)

        # 调用函数时会自动注入依赖
        my_function()  # db 和 config 会被自动传入

    不保留签名，直接装饰
        保留签名：使用get方法获取依赖
        再写一个函数式装饰器我认为没必要

    """
    global_dependencies: dict[str, Any] = {}

    def __init__(self, func: Callable[..., Any]) -> None:
        self.func = func

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        sig = signature(self.func)
        # 只注入目标函数声明的参数
        for name, dep in AstrbotInjector.global_dependencies.items():
            if name in sig.parameters and name not in kwargs:
                kwargs[name] = dep
        return self.func(*args, **kwargs)

    @classmethod
    def set(cls, name: str, value: Any) -> None:
        cls.global_dependencies[name] = value

    @classmethod
    def get(cls, name: str) -> Any:
        return cls.global_dependencies.get(name)

    @classmethod
    def remove(cls, name: str) -> None:
        cls.global_dependencies.pop(name, None)


class AstrbotModuleMeta(type):
    """ 用于设置AstrbotModule的类属性
    """
    _modules_registry: dict[str, type] = {}

    _paths_impl: type[IAstrbotPaths] | None = None
    _config_entry_impl: type[IAstrbotConfigEntry[Any]] | None = None
    _database_impl: type[IAstrbotDatabase] | None = None

    _broker_impl: AsyncBroker | None = None

    # 单一实例
    _paths: IAstrbotPaths | None = None
    _config_entry : IAstrbotConfigEntry[Any] | None = None
    _database: IAstrbotDatabase | None = None

    # 其他元数据
    _pypi_name: str
    _name: str
    _module_type: AstrbotModuleType
    _info: PackageMetadata | None = None

    def __new__(cls, name: str, bases: tuple[type, ...], attrs: dict[str, Any]) -> type[IAstrbotModule]:
        # 检测类名冲突
        if name in cls._modules_registry:
            raise ValueError(f"模块冲突: {name}")
        cls._modules_registry[name] = super().__new__(cls, name, bases, attrs)

        # 检测是否实现了必要接口
        if (
            not isinstance(cls._modules_registry[name], IAstrbotModule) 
        ):
            raise TypeError(f"类 {name} 未实现 IAstrbotModule 协议")

        return cls._modules_registry[name]

    @property
    def Paths(cls) -> type[IAstrbotPaths]:
        impl = type(cls)._paths_impl
        if impl is None:
            if Paths_impl := AstrbotInjector.get("AstrbotPaths"):
                type(cls)._paths_impl = Paths_impl
                impl = Paths_impl
            else:
                raise RuntimeError("AstrbotPaths 未注入，请在启动时设置 AstrbotInjector.set('AstrbotPaths', <实现类>)")
        return impl

    @Paths.setter
    def Paths(cls, value: type[IAstrbotPaths]) -> None:
        type(cls)._paths_impl = value
        
    @property
    def ConfigEntry(cls) -> type[IAstrbotConfigEntry[Any]]:
        impl = type(cls)._config_entry_impl
        if impl is None:
            if ConfigEntry_impl := AstrbotInjector.get("AstrbotConfigEntry"):
                type(cls)._config_entry_impl = ConfigEntry_impl
                impl = ConfigEntry_impl
            else:
                raise RuntimeError("AstrbotConfigEntry 未注入，请在启动时设置 AstrbotInjector.set('AstrbotConfigEntry', <实现类>)")
        return impl

    @ConfigEntry.setter
    def ConfigEntry(cls, value: type[IAstrbotConfigEntry[Any]]) -> None:
        type(cls)._config_entry_impl = value

    @property
    def Database(cls) -> type[IAstrbotDatabase]:
        impl = type(cls)._database_impl
        if impl is None:
            if Database_impl := AstrbotInjector.get("AstrbotDatabase"):
                type(cls)._database_impl = Database_impl
                impl = Database_impl
            else:
                raise RuntimeError("AstrbotDatabase 未注入，请在启动时设置 AstrbotInjector.set('AstrbotDatabase', <实现类>)")
        return impl

    @Database.setter
    def Database(cls, value: type[IAstrbotDatabase]) -> None:
        type(cls)._database_impl = value

    # 实例

    @property
    def broker(cls) -> AsyncBroker:
        impl = type(cls)._broker_impl
        if impl is None:
            if broker_impl := AstrbotInjector.get("broker"):
                type(cls)._broker_impl = broker_impl
                impl = broker_impl
            else:
                raise RuntimeError("AsyncBroker 未注入，请在启动时设置 AstrbotInjector.set('broker', <全局单例>)")
        return impl

    @broker.setter
    def broker(cls, value: AsyncBroker) -> None:
        type(cls)._broker_impl = value

    @property
    def paths(cls) -> IAstrbotPaths:
        if cls._paths:
            return  cls._paths
        return cls.Paths.getPaths(cls.pypi_name)

    @paths.setter
    def paths(cls, value: IAstrbotPaths) -> None:
        cls._paths = value

    @property
    def database(cls) -> IAstrbotDatabase:
        if cls._database:
            return cls._database
        return cls.Database.connect(cls.paths.data / f"{cls.pypi_name}.db")

    @database.setter
    def database(cls, value: IAstrbotDatabase) -> None:
        cls._database = value

    # 其他属性
    @property
    def pypi_name(cls) -> str:
        return cls._pypi_name
    
    @pypi_name.setter
    def pypi_name(cls, value: str) -> None:
        # 检查是否是合法的PyPI包名
        value = canonicalize_name(value)  # 标准化名称
        cls._pypi_name: str = value

    @property
    def name(cls) -> str:
        return cls._name
    
    @name.setter
    def name(cls, value: str) -> None:
        cls._name: str = value
        logger.debug(f"注册：{cls._name}（{cls.pypi_name}）")

    @property
    def module_type(cls) -> AstrbotModuleType:
        return cls._module_type

    @module_type.setter
    def module_type(cls, value: str | AstrbotModuleType ) -> None:
        if isinstance(value, str):
            try:
                value = AstrbotModuleType[value.upper()]
            except KeyError:
                raise ValueError(f"未知的模块类型：{value}")
        
        cls._module_type: AstrbotModuleType = value

    @property
    def info(cls) -> PackageMetadata:
        if cls._info is None:
            try:
                dist: Distribution = distribution(cls.pypi_name)
                cls._info = dist.metadata
            except PackageNotFoundError:
                raise RuntimeError(f"未找到包：{cls.pypi_name}，请确认包已安装且名称正确！")
        return cls._info

    @info.setter
    def info(cls, value: PackageMetadata) -> None:
        cls._info = value


class AstrbotModule():
    """ 装饰器类，用于标记模块并自动提取元数据，注入抽象接口的具体实现 
    大写开头表示这是一个类
    小写开头表示这是一个实例
    注意：
        此类需要核心模块注入具体实现
    注入：
        核心模块负责注入具体实现
    """
    def __init__(
        self,
        pypi_name: str,
        name: str,
        module_type: AstrbotModuleType,
        info: PackageMetadata | None = None
    ):
        self.pypi_name = pypi_name
        self.name = name
        self.module_type = module_type
        self.info = info

    def __call__(self, cls: type) -> type[IAstrbotModule]:
        DecoratedClass = AstrbotModuleMeta(cls.__name__, (cls,), {})
        DecoratedClass.pypi_name = self.pypi_name
        DecoratedClass.name = self.name
        DecoratedClass.module_type = self.module_type
        if self.info is not None:
            DecoratedClass.info = self.info
        return DecoratedClass


if __name__ == "__main__":
    @AstrbotModule("astrbot_canary_api", "canary_test", AstrbotModuleType.UNKNOWN)
    class TestModule:
        pass

    tm = TestModule()
    print(tm.info)