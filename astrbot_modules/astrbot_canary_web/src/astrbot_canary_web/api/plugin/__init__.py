from fastapi import APIRouter

__all__ = ["plugin_router"]

plugin_router: APIRouter = APIRouter(prefix="/plugin", tags=["Plugin"])