from logging import getLogger

from astrbot_canary_api import (
    IAstrbotLogHandler,
    LogHistoryResponseData,
)
from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter

from astrbot_canary_web.models import Response

logger = getLogger("astrbot.module.log_history")

__all__ = ["log_history_router"]

log_history_router: APIRouter = APIRouter(prefix="/log-history", tags=["Log History"])


@log_history_router.get("")
@inject
async def get_log_history(
    handler: FromDishka[IAstrbotLogHandler],
) -> Response[LogHistoryResponseData]:
    data: LogHistoryResponseData = await handler.get_log_history()
    return Response[LogHistoryResponseData].ok(data=data)
