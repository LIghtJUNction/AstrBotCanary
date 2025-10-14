import os

from astrbot_canary_api.interface import IAstrbotPaths
from pathlib import Path
from dotenv import load_dotenv

class AstrbotPaths():
    """Class to manage and provide paths used by Astrbot Canary."""
    load_dotenv()
    astrbot_root: Path = Path(os.getenv("ASTRBOT_ROOT", Path.home() / ".astrbot"))
    pypi_name: str

    @classmethod
    def root(cls, pypi_name: str) -> IAstrbotPaths:
        """ 返回模块路径根 """
        instance: IAstrbotPaths = cls()
        instance.pypi_name = pypi_name
        return instance
    
    @property
    def config(self) -> Path:
        """ 返回模块配置目录 """
        config_path = self.astrbot_root / "config" / self.pypi_name
        config_path.mkdir(parents=True, exist_ok=True)
        return config_path
    
    @property
    def data(self) -> Path:
        """ 返回模块数据目录 """
        data_path = self.astrbot_root / "data" / self.pypi_name
        data_path.mkdir(parents=True, exist_ok=True)
        return data_path
    
    @property
    def log(self) -> Path:
        """ 返回模块日志目录 """
        log_path = self.astrbot_root / "logs" / self.pypi_name
        log_path.mkdir(parents=True, exist_ok=True)
        return log_path
    
