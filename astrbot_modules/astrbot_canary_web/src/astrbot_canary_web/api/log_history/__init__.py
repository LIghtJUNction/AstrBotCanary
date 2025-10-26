from typing import Protocol, runtime_checkable

from astrbot_injector import AstrbotInjector
from astrbot_canary_api import IAstrbotLogHandler, LogHistoryResponseData
from fastapi import APIRouter

from astrbot_canary_web.models import Response

__all__ = ["log_history_router"]

log_history_router: APIRouter = APIRouter(prefix="/log-history", tags=["Log History"])


@runtime_checkable
class IAstrbotLogHandlerProtocol(Protocol):
    async def get_log_history(self) -> LogHistoryResponseData: ...


handler: IAstrbotLogHandler | None = None
handler_obj = AstrbotInjector.get("AsyncAstrbotLogHandler")
if handler_obj is not None and isinstance(handler_obj, IAstrbotLogHandlerProtocol):
    handler = handler_obj


@log_history_router.get("")
async def get_log_history() -> Response[LogHistoryResponseData]:
    if handler is None:
        msg = "未发现注入的handler"
        raise RuntimeError(msg)

    data: LogHistoryResponseData = await handler.get_log_history()
    return Response[LogHistoryResponseData].ok(data=data)
