"""
title: AstrbotCanary web 模块
version: v1.0.0
status: dev
authors: [LIghtJUNction]
owners: [LIghtJUNction]
created: 2025-10-09
updated: 2025-10-09
"""

from ..base import AstrbotBaseModule, ModuleType

from logging import getLogger
from robyn import Robyn
import datetime
import asyncio
import jwt


logger = getLogger("AstrbotCanary.Web")

class AstrbotWeb(AstrbotBaseModule):
    """Web UI 模块
    使用官方astrbot前端
    """
    TYPE = ModuleType.WEB

    @classmethod
    def Awake(cls):
        """自身初始化
        """
        logger.info("AstrbotWeb Awake")
    @classmethod
    def Start(cls, args: list[str]):
        """在Awake之后调用
        args: 启动参数
        """
        logger.info(f"AstrbotWeb Start with args: {args}")






    
"""Web模块规范
Web模块需要的参数args:
host = list[0]
port = list[1]
astrbot_root = list[2] (可选，默认"~/.astrbot/")
将从astrbot_root/metadata.toml读取webroot文件夹地址
并加载

"""