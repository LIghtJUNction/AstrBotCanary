from __future__ import annotations
from typing import Any, ClassVar, Generic, Literal, Self, TypeVar
from pydantic import BaseModel, Field
from sqlalchemy import Integer, String
from sqlalchemy.orm import declarative_base, mapped_column, Mapped


Base = declarative_base()

class User(Base):
    """SQLAlchemy ORM model for users.

    Fields are annotated with ``Mapped[...]`` to provide accurate static typing
    for tools like Pylance and mypy when using sqlalchemy-stubs.
    """
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    jwt_secret: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<User id={self.id!r} username={self.username!r}>"

    def to_dict(self) -> dict[str, Any]:
        """Return a small serializable representation of the user.

        Note: do not expose password or jwt_secret in production APIs.
        """
        return {"id": self.id, "username": self.username}

"""
# 响应包结构：
{
    status: str | None,
    message: str | None,
    data : dict | list | None
}  
"""

DataT = TypeVar("DataT")

class Response(BaseModel,Generic[DataT]):
    deps: ClassVar[dict[str, Any]] = {}
    status: Literal["ok", "error"] = "ok"
    message: str | None = None
    data: DataT | None = None
    @classmethod
    def ok(cls, data: DataT | None = None, message: str | None = "ok", **data_fields: Any) -> Self:
        """
        Create an OK response.

        You can call in any of these ways:
        - Response[LoginResponse].ok(LoginResponse(...))
        - Response[LoginResponse].ok({"username":..., "token": ...})
        - Response[LoginResponse].ok(username=..., token=...)
        """
        if data is None and data_fields:
            # accept kwargs to construct the inner data dict
            data = data_fields  # type: ignore
        return cls(status="ok", message=message, data=data)

    @classmethod
    def error(cls, message: str | None = "error") -> Self:
        return cls(status="error", message=message, data=None)


if __name__ == "__main__":
    class _Request(BaseModel):
        username: str = Field(..., min_length=7)
        password: str = Field(..., min_length=8)
    class LoginResponse(BaseModel):
        username: str | None = None
        token: str | None = None


    # 测试
    req = _Request(username="username", password="password")
    print(req)

    resp = Response[LoginResponse].ok(username=req.username, token="token")
    print(resp)