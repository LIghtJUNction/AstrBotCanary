from robyn import SubRouter

__all__ = ["t2i_router"]

t2i_router: SubRouter = SubRouter(__file__, prefix="/t2i")