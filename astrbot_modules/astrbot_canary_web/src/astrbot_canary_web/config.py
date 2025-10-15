from pathlib import Path
from pydantic import BaseModel

class AstrbotCanaryWebConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 6185
    webroot: Path
