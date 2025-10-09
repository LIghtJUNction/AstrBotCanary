from pathlib import Path
from dotenv import load_dotenv
import os

from logging import getLogger
logger = getLogger("astrbot_canary.base.paths")

class PathsMeta(type):
    load_dotenv()
    _root: Path | None = None
    @property
    def root(cls) -> Path:
        """Astrbot 根目录
        """
        if cls._root is None:
            from astrbot_canary.base.config import AstrbotConfig
            config = AstrbotConfig()
            cls._root = config.ROOT.expanduser().resolve()
        return cls._root
    
    @root.setter
    def root(cls, value: str | Path) -> None:
        """设置 Astrbot 根目录
        """
        if isinstance(value, str):
            value = Path(value)
        cls._root = value.expanduser().resolve()
        os.environ["ASTRBOT_ROOT"] = str(cls._root)
        return

    @property
    def metadata(cls) -> Path:
        """Astrbot 元数据目录
        """
        return cls.root / "metadata.toml"
    
    def __getattr__(cls, name: str) -> Path:
        return cls.root / name

class Paths(metaclass=PathsMeta):
    """统一路径管理类
    """
    @classmethod
    def sync(cls):
        """
        刷新路径缓存
        """
        load_dotenv()
        ASTRBOT_ROOT = os.getenv("ASTRBOT_ROOT") 
        if ASTRBOT_ROOT is not None:
            PathsMeta.root = Path(ASTRBOT_ROOT).expanduser().resolve()
        

    @classmethod
    def getDir(cls, name: str) -> Path:
        """
        获取指定目录路径
        """
        return cls.root / name


if __name__ == "__main__":

    print(Paths.root)
    print(Paths.metadata)
    print(Paths.plugins)
    print(Paths.logs)
    print(Paths.getDir("test/struct\\hhhu///hbhjbjh\\\\efef"))
    # n = 10000
    # for _ in range(n):
    #    _path = f"dir{_}"
    #    print(Paths.getDir(_path))
