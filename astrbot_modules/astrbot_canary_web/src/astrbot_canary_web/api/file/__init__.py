from fastapi import APIRouter
__all__ = ["file_router"]

file_router: APIRouter = APIRouter(prefix="/file", tags=["File"])