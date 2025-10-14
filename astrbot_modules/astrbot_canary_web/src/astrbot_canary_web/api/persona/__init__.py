from robyn import SubRouter

__all__ = ["persona_router"]

persona_router: SubRouter = SubRouter(__file__, prefix="/persona")