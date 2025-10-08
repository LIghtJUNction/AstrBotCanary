"""
title: AstrbotCanary插件基类
version: v1.0
status: dev
authors: [LIghtJUNction]
owners: [LIghtJUNction]
created: 2025-10-08
updated: 2025-10-08
"""

from abc import ABC, abstractmethod
from enum import Enum

class ModuleType(Enum):
    LOADER = "loader"   # 001 #加载插件
    CORE = "core"       # 002 #核心组件
    WEB = "web"         # 003 #Web模块
    TUI = "tui"         # 004 #终端富交互
    GUI = "gui"         # 005 #桌面GUI
    
class AstrbotBaseModule(ABC):
    """
    AstrbotCanary模块基类
    """
    TYPE : ModuleType
    
    @classmethod
    @abstractmethod
    def Awake(cls):
        """自身初始化
        """
        pass
    
    @classmethod
    @abstractmethod
    def Start(cls,args: list[str]):
        """在Awake之后调用
        args: 启动参数
        """
        pass