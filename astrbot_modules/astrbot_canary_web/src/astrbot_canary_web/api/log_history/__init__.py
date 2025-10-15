from fastapi import APIRouter

__all__ = ["log_history_router"]

log_history_router: APIRouter = APIRouter(prefix="/log_history", tags=["Log History"])