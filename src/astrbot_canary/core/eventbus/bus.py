"""
title: AstrbotCanary Event Bus
version: v1.0.0
status: dev
authors: [LIghtJUNction]
owners: [LIghtJUNction]
created: 2025-10-08
updated: 2025-10-08
"""
from ...base import AstrbotBaseModule

from logging import getLogger

logger = getLogger("AstrbotCanary.core.EventBus")

class AstrbotEventBus(AstrbotBaseModule):
    """
    AstrbotCanary事件总线
    """

    @classmethod
    def Awake(cls):
        """自身初始化
        """
        logger.info("AstrbotEventBus Awake")

    @classmethod
    def Start(cls, args: list[str]):
        """在Awake之后调用
        args: 启动参数
        """
        logger.info("AstrbotEventBus Start")