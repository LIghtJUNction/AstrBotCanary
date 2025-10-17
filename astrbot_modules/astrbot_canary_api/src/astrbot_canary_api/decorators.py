
from importlib.metadata import Distribution, distribution , PackageMetadata
from pydantic import BaseModel

from astrbot_canary_api import IAstrbotConfig, IAstrbotDatabase, IAstrbotPaths
from taskiq import AsyncBroker

from astrbot_canary_api.interface import IAstrbotConfigEntry

"""
取名为 info 是模仿BepInEx
灵感来自：BepInExAutoPlugin
"""
class AstrbotModuleMeta(type):
    """ 用于设置AstrbotModule的类属性
    """
    _paths_impl: type[IAstrbotPaths] | None = None
    _config_impl: type[IAstrbotConfig] | None = None
    _config_entry_impl: type[IAstrbotConfigEntry[BaseModel]] | None = None
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
    def Config(cls) -> type[IAstrbotConfig]:
        impl = type(cls)._config_impl
        if impl is None:
            raise RuntimeError("IAstrbotConfig 未注入，请在启动时设置 AstrbotModule.Config = <实现类>")
        return impl

    @Config.setter
    def Config(cls, value: type[IAstrbotConfig]) -> None:
        type(cls)._config_impl = value

    @property
    def ConfigEntry(cls) -> type[IAstrbotConfigEntry[BaseModel]]:
        impl = type(cls)._config_entry_impl
        if impl is None:
            raise RuntimeError("IAstrbotConfigEntry 未注入，请在启动时设置 AstrbotModule.ConfigEntry = <实现类>")
        return impl

    @ConfigEntry.setter
    def ConfigEntry(cls, value: type[IAstrbotConfigEntry[BaseModel]]) -> None:
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
    def __init__(self,pypi_name: str , info: PackageMetadata | None = None) -> None:
        self.info: PackageMetadata | None = info
        self.pypi_name: str = pypi_name

    def __call__(self, cls: type) -> type:
        cls.pypi_name = self.pypi_name
        if self.info is None:
            dist: Distribution = distribution(self.pypi_name)
            meta: PackageMetadata = dist.metadata
            cls.info = meta
        else:
            cls.info = self.info
        impl_config = type(self).Config
        impl_config_entry = type(self).ConfigEntry
        impl_paths = type(self).Paths
        impl_db = type(self).Database

        # 注入实现
        cls.Config = impl_config
        cls.Paths = impl_paths
        cls.Database = impl_db
        cls.ConfigEntry = impl_config_entry

        # 创建实例
        cls.config = impl_config.getConfig()
        cls.paths = impl_paths.getPaths(cls.pypi_name)
        cls.database = impl_db.connect(cls.paths.data / f"{cls.pypi_name}.db")

        return cls

if __name__ == "__main__":
    @AstrbotModule(pypi_name="astrbot_canary_api")
    class TestModule:
        pass

    tm = TestModule()
    print(tm.info)