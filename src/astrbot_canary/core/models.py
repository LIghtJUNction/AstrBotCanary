from __future__ import annotations

from astrbot_canary_api.enums import AstrbotBrokerType, AstrbotResultBackendType
from pydantic import BaseModel


class AstrbotRootConfig(BaseModel):
    """核心模块配置项."""

    modules: list[str]
    """ 发现的模块 """
    boot: list[str]
    """ 启动Astrbot-模块启动顺序 """
    log_what: str = "astrbot"
    """ 抓谁的日志? """
    log_maxsize: int = 500
    """ 日志缓存最大数量--这里是给web模块特供的handler使用的 """
    broker_type: str = AstrbotBrokerType.INMEMORY.value
    """ 任务队列 broker 类型 """
    backend_type: str = AstrbotResultBackendType.INMEMORY.value
    """ 任务队列 backend 类型 """


class AstrbotTasksConfig(BaseModel):
    """任务队列配置项.

    Args:
        ... : _description_

    Returns:
        ... : _description_

    """

    broker_type: str = AstrbotBrokerType.INMEMORY.value
    backend_type: str = AstrbotResultBackendType.INMEMORY.value
