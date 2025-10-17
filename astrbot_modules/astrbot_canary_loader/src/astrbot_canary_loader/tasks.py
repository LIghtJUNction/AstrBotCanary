from __future__ import annotations
from collections.abc import Callable
from types import CoroutineType
from typing import Any

from taskiq import TaskiqEvents, TaskiqState
from taskiq.abc.broker import EventHandler

from logging import getLogger
logger = getLogger("astrbot_canary.module.loader.tasks")


class AstrbotCanaryLoaderTasks:
    broker: BROKER_TYPE
    EventHandlers: list[EventHandler]
    tasks: list[Callable[..., CoroutineType[Any, Any, Any]]]

    def __init__(self, broker: BROKER_TYPE):
        self.broker = broker

    @classmethod
    def register(cls, broker: BROKER_TYPE) -> AstrbotCanaryLoaderTasks:
        instance = cls(broker)
        
        @broker.on_event(TaskiqEvents.CLIENT_STARTUP)
        async def start(state: TaskiqState) -> None:
            logger.info("AstrbotCanaryLoaderTasks client started.")
            return None


        @broker.on_event(TaskiqEvents.CLIENT_SHUTDOWN)
        async def shutdown(state: TaskiqState) -> None:
            logger.info("AstrbotCanaryLoaderTasks client shutdown.")
            return None
        
        @broker.task(
            task_name="astrbot://canary_loader/ping",
            description="A simple ping task to check if the task broker is working.",
        )
        async def ping() -> str:
            print("Ping task executed.")
            return "pong"


        cls.EventHandlers = [start, shutdown]

        cls.tasks= [ping]
        return instance



    
    