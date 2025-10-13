from __future__ import annotations

from taskiq import TaskiqEvents, TaskiqState
from taskiq.abc.broker import EventHandler
from astrbot_canary_api.types import BROKER_TYPE
from logging import getLogger
logger = getLogger("astrbot_canary.module.loader.tasks")


class AstrbotCanaryLoaderTasks:
    broker: BROKER_TYPE
    EventHandlers: list[EventHandler]

    def __init__(self, broker: BROKER_TYPE):
        self.broker = broker

    @classmethod
    def register(cls, broker: BROKER_TYPE) -> AstrbotCanaryLoaderTasks:
        instance = cls(broker)
        
        @broker.on_event(TaskiqEvents.CLIENT_STARTUP)
        async def ping(state: TaskiqState) -> None:
            logger.info("AstrbotCanaryLoaderTasks client started.")
            return None

        cls.EventHandlers = [ping]
        return instance



    
    