from fastapi import APIRouter

__all__ = ["config_router"]

config_router: APIRouter = APIRouter(prefix="/config", tags=["Config"])
