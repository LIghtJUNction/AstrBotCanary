from pydantic import BaseModel
from taskiq import AsyncBroker, AsyncResultBackend

__all__ = [
    "BROKER_TYPE",
]

type BROKER_TYPE = AsyncBroker
type RESULT_BACKEND_TYPE = AsyncResultBackend[BaseModel]