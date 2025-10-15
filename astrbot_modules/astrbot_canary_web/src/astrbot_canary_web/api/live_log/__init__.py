from fastapi import APIRouter

__all__ = ["live_log_router"]

live_log_router: APIRouter = APIRouter(prefix="/live_log", tags=["Live Log"])