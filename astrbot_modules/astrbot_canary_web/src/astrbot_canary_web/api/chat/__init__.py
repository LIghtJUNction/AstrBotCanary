from fastapi import APIRouter

__all__ = ["chat_router"]

chat_router: APIRouter = APIRouter(prefix="/chat", tags=["Chat"])
