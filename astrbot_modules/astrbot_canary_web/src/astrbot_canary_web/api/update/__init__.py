from robyn import SubRouter

__all__ = ["update_router"]

update_router: SubRouter = SubRouter(__file__, prefix="/update")