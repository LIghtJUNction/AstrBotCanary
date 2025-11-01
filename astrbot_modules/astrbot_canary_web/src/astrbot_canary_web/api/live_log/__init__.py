from logging import getLogger

from astrbot_canary_api import (
    IAstrbotLogHandler,
)
from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from astrbot_canary_web.models import Response

logger = getLogger("astrbot.module.live_log")

__all__ = ["live_log_router"]

live_log_router: APIRouter = APIRouter(prefix="/live-log", tags=["Live Log"])


@live_log_router.get("")
@inject
async def get_live_log(
    handler: FromDishka[IAstrbotLogHandler],
) -> StreamingResponse:
    logger.info("New live log client connected")
    return Response.sse(stream=handler.event_stream())
