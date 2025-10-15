from fastapi import APIRouter

__all__ = ["session_router"]

session_router: APIRouter = APIRouter(prefix="/session", tags=["Session"])