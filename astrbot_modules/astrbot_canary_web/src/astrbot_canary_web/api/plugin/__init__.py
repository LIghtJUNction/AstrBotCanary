from robyn import SubRouter

__all__ = ["plugin_router"]

plugin_router: SubRouter = SubRouter(__file__, prefix="/plugin")