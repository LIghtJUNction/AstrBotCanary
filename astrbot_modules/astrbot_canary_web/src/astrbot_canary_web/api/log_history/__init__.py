from robyn import SubRouter

__all__ = ["log_history_router"]

log_history_router: SubRouter = SubRouter(__file__, prefix="/log_history")