from fastapi import APIRouter

__all__ = ["update_router"]

update_router: APIRouter = APIRouter(prefix="/update", tags=["Update"])
