from pydantic import BaseModel


class LogHistoryItem(BaseModel):
    level: str
    time: str
    data: str


class LogSSEItem(BaseModel):
    type: str
    level: str
    time: str
    data: str


class LogHistoryResponseData(BaseModel):
    logs: list[LogHistoryItem]
