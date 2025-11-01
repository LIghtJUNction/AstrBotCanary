from __future__ import annotations

from collections.abc import AsyncIterable
from typing import Any, Generic, Literal, TypeVar, overload

from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# SQLAlchemy Base
class Base(DeclarativeBase):
    pass
# region User 模型
class User(Base):
    """使用 fastapi-users 的用户模型。

    fastapi-users 处理所有密码哈希、验证和 JWT 令牌签发/验证。
    """

    __tablename__ = "users"

    # fastapi-users 要求的字段
    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    is_verified: Mapped[bool] = mapped_column(default=False)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<User {self.username!r}>"

    def to_dict(self) -> dict[str, Any]:
        """返回用户的简要序列化表示.

        注意: 在生产 API 中不要暴露 hashed_password.
        """
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
        }


# endregion


# region Response 模型
"""
# 响应包结构:
{
    status: str | None,
    message: str | None,
    data : dict | list | None
}
"""

DataT = TypeVar("DataT")


class Response(BaseModel, Generic[DataT]):
    status: Literal["ok", "error"] = "ok"
    message: str | None = None
    data: DataT | None = None

    # 两个重载:
    # 1) 调用者传入具体的 DataT,返回 Response[DataT]
    @overload
    @classmethod
    def ok(cls, data: DataT, message: str | None = "ok") -> Response[DataT]: ...

    # 2) 调用者使用 kwargs 构建匿名 dict 数据,返回 Response[dict[str, Any]]
    @overload
    @classmethod
    def ok(
        cls,
        data: None = None,
        message: str | None = "ok",
        **data_fields: object,
    ) -> Response[dict[str, object]]: ...

    @classmethod
    def ok(
        cls,
        data: Any | None = None,
        message: str | None = "ok",
        **data_fields: Any,
    ) -> Response[dict[str, Any]] | Response[DataT]:
        """创建一个成功响应(OK)..

        使用方式示例:
        - Response[LoginResponse].ok(LoginResponse(...))
        - Response[LoginResponse].ok({"username":..., "token": ...})
        - Response[LoginResponse].ok(username=..., token=...)
        """
        if data is None and data_fields:
            # 如果传入 kwargs,则把它们当作一个简单的 dict 作为 data
            data = dict(data_fields)
        return cls(status="ok", message=message, data=data)

    @classmethod
    def error(cls, message: str | None = "error") -> Response[DataT]:
        return cls(status="error", message=message, data=None)

    @staticmethod
    def sse(
        stream: AsyncIterable[str],
        headers: dict[str, str] | None = None,
    ) -> StreamingResponse:
        r"""用于返回标准 SSE 响应.
        stream: async 生成器,yield 每条 data: ...\n\n
        headers: 可选自定义响应头(如 Content-Type,Cache-Control 等).
        """
        default_headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
        }
        if headers:
            default_headers.update(headers)
        return StreamingResponse(stream, headers=default_headers)


# region 日志消息模型
