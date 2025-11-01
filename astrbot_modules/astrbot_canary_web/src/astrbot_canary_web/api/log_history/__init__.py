from logging import getLogger

from astrbot_canary_api import (
    IAstrbotLogHandler,
    LogHistoryResponseData,
    ProviderRegistry,
)
from fastapi import APIRouter

from astrbot_canary_web.models import Response

logger = getLogger("astrbot.module.log_history")

__all__ = ["log_history_router"]

log_history_router: APIRouter = APIRouter(prefix="/log-history", tags=["Log History"])


def _get_log_handler() -> IAstrbotLogHandler | None:
    """Get the log handler from dishka container."""
    try:
        container = ProviderRegistry.get_container()
        return container.get(IAstrbotLogHandler)
    except RuntimeError:
        logger.warning("Failed to get log handler from container", exc_info=True)
        return None


@log_history_router.get("")
async def get_log_history() -> Response[LogHistoryResponseData]:
    handler = _get_log_handler()
    if handler is None:
        msg = "未发现注入的handler"
        raise RuntimeError(msg)

    data: LogHistoryResponseData = await handler.get_log_history()
    return Response[LogHistoryResponseData].ok(data=data)
