from robyn import SubRouter

__all__ = ["stat_router"]

stat_router: SubRouter = SubRouter(__file__, prefix="/stat")