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
from inspect import signature
from importlib.metadata import Distribution, distribution , PackageMetadata
from taskiq import AsyncBroker
from typing import Any, ParamSpec, TypeVar
from collections.abc import Callable

from astrbot_canary_api import (
    AstrbotModuleType, 
    IAstrbotDatabase, 
    IAstrbotPaths,
    IAstrbotConfigEntry
)

"""
取名为 info 是模仿BepInEx
灵感来自：BepInExAutoPlugin
"""
class AstrbotModuleMeta(type):
    """ 用于设置AstrbotModule的类属性
    """
    _paths_impl: type[IAstrbotPaths] | None = None
    _config_entry_impl: type[IAstrbotConfigEntry[Any]] | None = None
    _database_impl: type[IAstrbotDatabase] | None = None
    _broker_impl: AsyncBroker | None = None

    @property
    def Paths(cls) -> type[IAstrbotPaths]:
        impl = type(cls)._paths_impl
        if impl is None:
            raise RuntimeError("IAstrbotPaths 未注入，请在启动时设置 AstrbotModule.Paths = <实现类>")
        return impl

    @Paths.setter
    def Paths(cls, value: type[IAstrbotPaths]) -> None:
        type(cls)._paths_impl = value


    @property
    def ConfigEntry(cls) -> type[IAstrbotConfigEntry[Any]]:
        impl = type(cls)._config_entry_impl
        if impl is None:
            raise RuntimeError("IAstrbotConfigEntry 未注入，请在启动时设置 AstrbotModule.ConfigEntry = <实现类>")
        return impl

    @ConfigEntry.setter
    def ConfigEntry(cls, value: type[IAstrbotConfigEntry[Any]]) -> None:
        type(cls)._config_entry_impl = value

    @property
    def Database(cls) -> type[IAstrbotDatabase]:
        impl = type(cls)._database_impl
        if impl is None:
            raise RuntimeError("IAstrbotDatabase 未注入，请在启动时设置 AstrbotModule.Database = <实现类>")
        return impl

    @Database.setter
    def Database(cls, value: type[IAstrbotDatabase]) -> None:
        type(cls)._database_impl = value

    @property
    def broker(cls) -> AsyncBroker:
        impl = type(cls)._broker_impl
        if impl is None:
            raise RuntimeError("AsyncBroker 未注入，请在启动时设置 AstrbotModule.broker = <实现类>")
        return impl

    @broker.setter
    def broker(cls, value: AsyncBroker) -> None:
        type(cls)._broker_impl = value

class AstrbotModule(metaclass=AstrbotModuleMeta):
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
            pypi_name: str ,
            name: str,
            module_type: AstrbotModuleType,
            info: PackageMetadata | None = None
        ) -> None:
        self.info: PackageMetadata | None = info
        self.pypi_name: str = pypi_name
        self.name : str = name
        self.module_type : AstrbotModuleType = module_type

    def __call__(self, cls: type) -> type:
        # 注入元数据
        cls.pypi_name = self.pypi_name
        cls.name = self.name
        cls.module_type = self.module_type
        if self.info is None:
            dist: Distribution = distribution(self.pypi_name)
            meta: PackageMetadata = dist.metadata
            cls.info = meta
        else:
            cls.info = self.info

        impl_config_entry = type(self).ConfigEntry
        impl_paths = type(self).Paths
        impl_db = type(self).Database

        # 注入实现
        cls.Paths = impl_paths
        cls.Database = impl_db
        cls.ConfigEntry = impl_config_entry

        # 创建实例

        cls.paths = impl_paths.getPaths(cls.pypi_name)
        cls.database = impl_db.connect(cls.paths.data / f"{cls.pypi_name}.db")

        return cls

# 类型安全的依赖注入装饰器（推荐用法）
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

    # 兼容老用法：@AstrbotInjector
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


if __name__ == "__main__":
    @AstrbotModule("astrbot_canary_api", "canary_test", AstrbotModuleType.UNKNOWN)
    class TestModule:
        pass

    tm = TestModule()
    print(tm.info)