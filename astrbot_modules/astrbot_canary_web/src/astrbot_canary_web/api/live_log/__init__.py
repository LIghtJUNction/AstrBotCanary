from logging import getLogger

from astrbot_canary_api import IAstrbotLogHandler, ProviderRegistry
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from astrbot_canary_web.models import Response

logger = getLogger("astrbot.module.live_log")

__all__ = ["live_log_router"]

live_log_router: APIRouter = APIRouter(prefix="/live-log", tags=["Live Log"])


def _get_log_handler() -> IAstrbotLogHandler | None:
    """Get the log handler from dishka container."""
    try:
        container = ProviderRegistry.get_container()
        return container.get(IAstrbotLogHandler)
    except RuntimeError:
        logger.warning("Failed to get log handler from container", exc_info=True)
        return None


@live_log_router.get("")
async def get_live_log() -> StreamingResponse:
    logger.info("New live log client connected")
    handler = _get_log_handler()
    if handler is None:
        msg = "未发现注入的日志钩子"
        raise RuntimeError(msg)
    return Response.sse(stream=handler.event_stream())
