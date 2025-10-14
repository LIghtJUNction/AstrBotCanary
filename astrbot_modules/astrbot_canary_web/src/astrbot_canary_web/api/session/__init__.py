from robyn import SubRouter

__all__ = ["session_router"]

session_router: SubRouter = SubRouter(__file__, prefix="/session")