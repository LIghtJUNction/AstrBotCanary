from fastapi import APIRouter

__all__ = ["stat_router"]

stat_router: APIRouter = APIRouter(prefix="/stat", tags=["Stat"])
