from robyn import SubRouter

__all__ = ["conversation_router"]

conversation_router: SubRouter = SubRouter(__file__, prefix="/conversation")