from fastapi import APIRouter

__all__ = ["t2i_router"]

t2i_router: APIRouter = APIRouter(prefix="/t2i", tags=["Text to Image"])