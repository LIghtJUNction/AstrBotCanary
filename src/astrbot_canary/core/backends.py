from pydantic import BaseModel, Field

from astrbot_canary_api import AstrbotResultBackendType


class AstrbotBackendConfig(BaseModel):
    backend_type: str = Field(default=AstrbotResultBackendType.NONE.value, description="The type of backend to use, e.g., 'sqlalchemy', 'mongodb', etc.")
    ...