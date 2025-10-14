from robyn import SubRouter

__all__ = ["live_log_router"]

live_log_router: SubRouter = SubRouter(__file__, prefix="/live_log")