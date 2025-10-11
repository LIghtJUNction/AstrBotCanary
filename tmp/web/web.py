"""
title: AstrbotCanary web 模块
version: v1.0.0
status: dev
authors: [LIghtJUNction]
owners: [LIghtJUNction]
created: 2025-10-09
updated: 2025-10-09
"""

import logging
from pathlib import Path

from click import confirm
from pydantic_core import Url

from .routes import AstrbotWebRoutes

from ..base import AstrbotModuleAPI,AstrbotConfig

from logging import getLogger
from robyn import Robyn
import zipfile

logger = getLogger("AstrbotCanary.Web")

class AstrbotWeb(AstrbotModuleAPI.AstrbotBaseModule):
    """Web UI 模块
    使用官方astrbot前端
    """
    TYPE: AstrbotModuleAPI.ModuleType = AstrbotModuleAPI.ModuleType.WEB
    app: Robyn | None = None
    _initialized: bool = False
    @classmethod
    def Awake(cls):
        """自身初始化
        """
        logger.info("AstrbotWeb Awake")
        config: AstrbotConfig = AstrbotConfig.getConfig()
        
        logger.info(f"Webroot path: {config.webroot}")
        # 检查webroot是否存在
        if not cls.check_webroot(config.webroot):
            if confirm("Webroot does not exist. Create it?",default=True):
                config.webroot.mkdir(parents=True, exist_ok=True)
                cls.download_official_frontend_to(config.webroot)
                # 多一个dist.zip文件
                   
        # 如果包含dist.zip 直接解压并删除
        if (config.webroot / "dist.zip").exists():
            cls.unzip_official_frontend(config.webroot / "dist.zip", config.webroot)

        cls.load_official_frontend(config.webroot, log_level=logging.INFO)

    @classmethod
    def Start(cls, args: list[str]):
        """在Awake之后调用
        args: 启动参数
        """
        logger.info(f"AstrbotWeb Start with args: {args}")


    @classmethod
    def check_webroot(cls, path: Path) -> bool:
        """简单检查webroot是否有效
        判断依据：文件夹存在且包含index.html 并且不能包含dist.zip
        """
        if path.exists() and path.is_dir() and (path / "dist" / "index.html").exists() and not (path / "dist.zip").exists():
            return True
        return False


    @classmethod
    def download_official_frontend_to(cls, path: Path):
        """下载官方前端到指定路径
        """
        # 如果目录非空，则提示用户确认是否清空
        if any(path.iterdir()):
            if not confirm(f"Directory {path} is not empty. Clear it?"):
                logger.warning("Aborting download due to non-empty directory.")
                return
            for item in path.iterdir():
                if item.is_dir():
                    import shutil
                    shutil.rmtree(item)
                else:
                    item.unlink()
        # 从GitHub下载最新的release版前端
        dashboard_release_url : Url = Url("https://astrbot-registry.soulter.top/download/astrbot-dashboard/latest/dist.zip")

        logger.info(f"Downloading official frontend from {dashboard_release_url} to {path}")

        AstrbotModuleAPI.Utils.download(dashboard_release_url, path / "dist.zip")
        
    @classmethod
    def unzip_official_frontend(cls, zip_path: Path, extract_to: Path):
        """解压官方前端
        """
        if not zip_path.exists() or not zip_path.is_file():
            logger.error(f"Zip file {zip_path} does not exist.")
            return
        logger.info(f"Unzipping {zip_path} to {extract_to}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        # 删除zip文件
        zip_path.unlink()

        
    @classmethod
    def load_official_frontend(cls, path: Path, log_level: int = logging.WARNING):
        """加载官方前端
        """
        logger.info(f"Loading official frontend from {(path / 'dist').resolve()}")
        frontend = path / "dist"
        logging.getLogger("robyn").setLevel(log_level)
        cls.app = Robyn(__file__)
        
        AstrbotWebRoutes.initialize(cls.app, frontend)
        
        cls._initialized = True
        
        cls.app.start()

"""Web模块规范
Web模块需要的参数args:
host = list[0]
port = list[1]
astrbot_root = list[2] (可选，默认"~/.astrbot/")
将从astrbot_root/metadata.toml读取webroot文件夹地址
并加载

"""