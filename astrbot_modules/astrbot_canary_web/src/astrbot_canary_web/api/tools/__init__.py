from fastapi import APIRouter

__all__ = ["tools_router"]

tools_router: APIRouter = APIRouter(prefix="/tools", tags=["Tools"])
