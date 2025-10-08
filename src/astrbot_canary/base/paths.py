from pathlib import Path
from dotenv import load_dotenv
import os

class PathsMeta(type):
    load_dotenv()
    _root: Path | None = None
    @property
    def root(cls) -> Path:
        """Astrbot 根目录
        """
        if cls._root is not None:
            return cls._root
        else:
            if "ASTRBOT_ROOT" in os.environ:
                cls._root = Path(os.environ["ASTRBOT_ROOT"]).expanduser().resolve()
            else:
                cls._root = Path("~/.astrbot/").expanduser().resolve()
            
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
        if os.environ.get("ASTRBOT_ROOT") is not None:
            PathsMeta.root = Path(os.environ["ASTRBOT_ROOT"]).expanduser().resolve()
        


if __name__ == "__main__":

    print(Paths.root)
    print(Paths.metadata)
    print(Paths.plugins)
