from fastapi import APIRouter

__all__ = ["persona_router"]

persona_router: APIRouter = APIRouter(prefix="/persona", tags=["Persona"])