from fastapi import APIRouter
__all__ = ["conversation_router"]

conversation_router: APIRouter = APIRouter(prefix="/conversation", tags=["Conversation"])