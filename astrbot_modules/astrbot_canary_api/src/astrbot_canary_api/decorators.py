
from importlib.metadata import Distribution, distribution , PackageMetadata
from pydantic import BaseModel

from astrbot_canary_api import IAstrbotConfig, IAstrbotDatabase, IAstrbotPaths
from taskiq import AsyncBroker

from astrbot_canary_api.interface import IAstrbotConfigEntry

"""
取名为 info 是模仿BepInEx
灵感来自：BepInExAutoPlugin
"""
class AstrbotModule:
    """ 装饰器类，用于标记模块并自动提取元数据，注入抽象接口的具体实现 
    大写开头表示这是一个类
    小写开头表示这是一个实例
    注意：
        此类需要核心模块注入具体实现
    注入：
        核心模块负责注入具体实现
    """
    Paths: type[IAstrbotPaths]
    Config: type[IAstrbotConfig]
    ConfigEntry: type[IAstrbotConfigEntry[BaseModel]]
    Database: type[IAstrbotDatabase]
    # 实例
    paths: IAstrbotPaths | None = None
    config: IAstrbotConfig | None = None
    database: IAstrbotDatabase | None = None
    broker: AsyncBroker | None = None

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
        cls.Config = self.Config
        cls.Paths = self.Paths
        cls.Database = self.Database
        # 创建实例
        cls.config = cls.Config.getConfig()
        cls.paths = cls.Paths.getPaths(cls.pypi_name)
        cls.database = cls.Database.connect(cls.paths.data / f"{cls.pypi_name}.db")

        return cls

if __name__ == "__main__":
    @AstrbotModule(pypi_name="astrbot_canary_api")
    class TestModule:
        pass

    tm = TestModule()
    print(tm.info)