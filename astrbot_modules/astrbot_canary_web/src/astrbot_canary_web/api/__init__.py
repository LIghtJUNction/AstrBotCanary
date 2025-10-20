from fastapi import APIRouter

from .auth import auth_router
from .chat import chat_router
from .config import config_router
from .conversation import conversation_router
from .file import file_router
from .live_log import live_log_router
from .log_history import log_history_router
from .persona import persona_router
from .plugin import plugin_router
from .session import session_router
from .stat import stat_router
from .t2i import t2i_router
from .tools import tools_router
from .update import update_router

api_router = APIRouter(prefix="/api", tags=["API"])

api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(config_router)
api_router.include_router(conversation_router)
api_router.include_router(file_router)
api_router.include_router(live_log_router)
api_router.include_router(log_history_router)
api_router.include_router(persona_router)
api_router.include_router(plugin_router)
api_router.include_router(session_router)
api_router.include_router(stat_router)
api_router.include_router(t2i_router)
api_router.include_router(tools_router)
api_router.include_router(update_router)

__all__ = [
    "api_router",
]
