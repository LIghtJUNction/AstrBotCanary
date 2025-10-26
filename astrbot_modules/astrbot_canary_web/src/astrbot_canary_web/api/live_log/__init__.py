from logging import getLogger
from typing import Protocol, runtime_checkable

from astrbot_injector import AstrbotInjector
from astrbot_canary_api.interface import IAstrbotLogHandler
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from astrbot_canary_web.models import Response

logger = getLogger("astrbot.module.live_log")

__all__ = ["live_log_router"]

live_log_router: APIRouter = APIRouter(prefix="/live-log", tags=["Live Log"])


@runtime_checkable
class IAstrbotLogHandlerProtocol(Protocol):
    def event_stream(self) -> None: ...


handler: IAstrbotLogHandler | None = AstrbotInjector.get("AsyncAstrbotLogHandler")


@live_log_router.get("")
async def get_live_log() -> StreamingResponse:
    logger.info("New live log client connected")
    if handler is None:
        msg = "未发现注入的日志钩子"
        raise RuntimeError(msg)
    return Response.sse(stream=handler.event_stream())
