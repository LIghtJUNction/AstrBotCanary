from robyn import SubRouter

__all__ = ["tools_router"]

tools_router: SubRouter = SubRouter(__file__, prefix="/tools")