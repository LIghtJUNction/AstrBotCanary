
from fastapi import APIRouter

from astrbot_canary_api.decorators import AstrbotInjector
from astrbot_canary_api.interface import IAstrbotLogHandler, LogHistoryResponseData

from astrbot_canary_web.models import Response

__all__ = ["log_history_router"]

log_history_router: APIRouter = APIRouter(prefix="/log-history", tags=["Log History"])

handler: IAstrbotLogHandler = AstrbotInjector.get("AsyncAstrbotLogHandler")

@log_history_router.get("")
async def get_log_history():
    data: LogHistoryResponseData = await handler.get_log_history()
    return Response[LogHistoryResponseData].ok(data=data)