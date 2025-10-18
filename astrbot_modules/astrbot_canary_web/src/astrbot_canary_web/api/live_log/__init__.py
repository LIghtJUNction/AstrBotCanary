from fastapi import APIRouter
from astrbot_canary_api.decorators import AstrbotInjector
from astrbot_canary_api.interface import IAstrbotLogHandler
from astrbot_canary_web.models import Response
from logging import getLogger

logger = getLogger("astrbot.module.live_log")

__all__ = ["live_log_router"]

live_log_router: APIRouter = APIRouter(prefix="/live-log", tags=["Live Log"])

handler: IAstrbotLogHandler = AstrbotInjector.get("AsyncAstrbotLogHandler")

@live_log_router.get("")
async def get_live_log():
    logger.info("New live log client connected")
    return Response.sse(handler.event_stream())