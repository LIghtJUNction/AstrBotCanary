from robyn import SubRouter

__all__ = ["chat_router"]

chat_router: SubRouter = SubRouter(__file__, prefix="/api/chat")