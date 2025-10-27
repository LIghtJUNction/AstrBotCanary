from __future__ import annotations

from os import getenv
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv
from packaging.utils import NormalizedName, canonicalize_name


class AstrbotPaths:
    """Class to manage and provide paths used by Astrbot Canary."""

    load_dotenv()
    astrbot_root: ClassVar[Path] = Path(getenv("ASTRBOT_ROOT", Path.home() / ".astrbot"))

    def __init__(self, pypi_name: str) -> None:
        self.pypi_name: str = pypi_name
        # 确保根目录存在
        self.astrbot_root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def getPaths(cls, pypi_name: str) -> AstrbotPaths:
        """返回Paths实例,用于访问模块的各类目录."""
        normalized_name: NormalizedName = canonicalize_name(pypi_name)
        instance: AstrbotPaths = cls(normalized_name)
        instance.pypi_name = normalized_name
        return instance

    @property
    def root(self) -> Path:
        """注意这不是Astrbot系统根.

        通过此属性获取模块根.
        """
        my_root = self.astrbot_root / "home" / self.pypi_name
        my_root.mkdir(parents=True, exist_ok=True)
        return my_root


    @property
    def config(self) -> Path:
        """返回模块配置目录.

        搭配 astrbot_config 使用.
        """
        config_path = self.astrbot_root / "config" / self.pypi_name
        config_path.mkdir(parents=True, exist_ok=True)
        return config_path


    @property
    def data(self) -> Path:
        """返回模块数据目录."""
        data_path = self.astrbot_root / "data" / self.pypi_name
        data_path.mkdir(parents=True, exist_ok=True)
        return data_path

    @property
    def log(self) -> Path:
        """返回模块日志目录."""
        log_path = self.astrbot_root / "logs" / self.pypi_name
        log_path.mkdir(parents=True, exist_ok=True)
        return log_path


    def reload(self) -> None:
        """重新加载环境变量."""
        load_dotenv()
        self.__class__.astrbot_root = Path(getenv("ASTRBOT_ROOT", Path.home() / ".astrbot"))

