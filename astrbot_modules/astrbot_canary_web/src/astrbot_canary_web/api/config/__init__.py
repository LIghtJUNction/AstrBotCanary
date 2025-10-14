from robyn import SubRouter

__all__ = ["config_router"]

config_router: SubRouter = SubRouter(__file__, prefix="/config")