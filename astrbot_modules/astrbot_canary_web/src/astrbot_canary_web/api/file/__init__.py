from robyn import SubRouter

__all__ = ["file_router"]

file_router: SubRouter = SubRouter(__file__, prefix="/file")