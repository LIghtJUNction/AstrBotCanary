from __future__ import annotations
from collections.abc import AsyncIterable
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any, ClassVar, Generic, Literal, Self, TypeVar, overload

from pydantic import BaseModel, Field
from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

from jwt import decode, encode # type: ignore
from fastapi.responses import StreamingResponse


# PyJWT
class Base(DeclarativeBase):
    ...
#region User 模型
class User(Base):
    """SQLAlchemy ORM 用户模型。

    存储用户的用户名、带盐密码哈希、随机盐值和用于签发/验证 JWT 的每用户对称密钥。
    所有密码学操作（加盐哈希、验证、JWT 签发/验证）均封装为实例/类方法。
    """
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String, primary_key=True, nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(String, nullable=False)  # 存储哈希（hex）
    salt: Mapped[str] = mapped_column(String, nullable=False)      # 存储随机盐（hex）
    jwt_secret: Mapped[str] = mapped_column(String, nullable=False)

    # PBKDF2 参数
    _HASH_ITERATIONS: ClassVar[int] = 100_000
    _HASH_NAME: ClassVar[str] = "sha256"

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<User {self.username!r} >"

    def to_dict(self) -> dict[str, Any]:
        """返回用户的简要序列化表示。

        注意：在生产 API 中不要暴露 password、salt 或 jwt_secret。
        """
        return {"username": self.username}
    
    # region 公共接口
    async def verify_password_async(self: "User", password: str) -> bool:
        salt_bytes = bytes.fromhex(self.salt)
        hash_bytes = hashlib.pbkdf2_hmac(
            self._HASH_NAME,
            password.encode(),
            salt_bytes,
            self._HASH_ITERATIONS,
        )
        return self.password == hash_bytes.hex()

    async def issue_token_async(self: "User", exp_days: int = 7) -> str:
        return self._generate_jwt(self.username, exp=exp_days)
    @classmethod
    async def create_and_issue_token(cls, session: AsyncSession, username: str, password: str, exp_days: int) -> tuple["User", str]:
        user = await cls._create(session, username=username, password=password)
        token = user._generate_jwt(username=username, exp=exp_days)
        return user, token

    @classmethod
    async def find_by_token_async(cls, session: AsyncSession, token: str, expected_iss: str | None = None) -> tuple["User", dict[str, Any]]:
        from typing import cast
        last_exc: Exception | None = None
        try:
            unverified = decode(token, options={"verify_signature": False})
        except Exception:
            unverified = None
        unverified = cast(dict[str, Any] | None, unverified)
        if isinstance(unverified, dict):
            aud = cast(str | None, unverified.get("aud"))
            if aud:
                candidate = await session.get(cls, aud)
                if candidate:
                    try:
                        payload = candidate._verify_jwt(token, expected_iss=expected_iss, expected_aud=aud)
                        return candidate, payload
                    except Exception as e:
                        last_exc = e
        result = await session.execute(select(cls))
        users = result.scalars().all()
        for user in users:
            try:
                payload = user._verify_jwt(token, expected_iss=expected_iss)
                return user, payload
            except Exception as e:
                last_exc = e
        raise LookupError("no user matches token") from last_exc

    async def update_password_async(self, session: AsyncSession, new_password: str) -> None:
        self._set_password(new_password)
        session.add(self)
        await session.flush()

    async def update_username_async(self, session: AsyncSession, new_username: str) -> None:
        exists = await session.get(User, new_username)
        if exists:
            raise ValueError("username already taken")
        self.username = new_username
        session.add(self)
        await session.flush()
    # endregion

    # region 内部方法
    @classmethod
    async def _create(cls, session: AsyncSession, username: str, password: str) -> "User":
        user = cls(
            username=username,
            salt=secrets.token_hex(16),
            jwt_secret=secrets.token_hex(32),
        )
        user._set_password(password)
        session.add(user)
        await session.flush()
        return user
    
    def _set_password(self, password: str) -> None:
        salt_bytes = bytes.fromhex(self.salt)
        hash_bytes = hashlib.pbkdf2_hmac(
            self._HASH_NAME,
            password.encode(),
            salt_bytes,
            self._HASH_ITERATIONS,
        )
        self.password = hash_bytes.hex()

    def _generate_jwt(self, username: str, exp: int = 7) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "iss": "AstrBotCanary",                # 签发者
            "sub": username,                        # 主题（用户唯一标识）
            "aud": username,                        # 接收方
            "exp": int((now + timedelta(days=exp)).timestamp()), # 过期时间
            "nbf": int(now.timestamp()),            # 生效时间
            "iat": int(now.timestamp()),            # 签发时间
            "jti": secrets.token_hex(8),            # JWT唯一ID
        }
        return encode(payload, self.jwt_secret, algorithm="HS256")
    
    def _verify_jwt(self, token: str, expected_iss: str | None = None, expected_aud: str | None = None, expected_sub: str | None = None) -> dict[str, Any]:
        payload = decode(
            token,
            self.jwt_secret,
            algorithms=["HS256"],
            audience=self.username
        )
        now = int(datetime.now(timezone.utc).timestamp())
        if expected_iss and payload.get("iss") != expected_iss:
            raise ValueError("issuer mismatch")
        if expected_aud and payload.get("aud") != expected_aud:
            raise ValueError("audience mismatch")
        if expected_sub and payload.get("sub") != expected_sub:
            raise ValueError("subject mismatch")
        if "nbf" in payload and payload["nbf"] > now:
            raise ValueError("token not yet valid")
        if "iat" in payload and payload["iat"] > now:
            raise ValueError("token issued in future")
        if "exp" in payload and payload["exp"] < now:
            raise ValueError("token expired")
        if "jti" not in payload:
            raise ValueError("missing JWT ID")
        return payload
        # endregion




#endregion


#region Response 模型
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

    status: Literal["ok", "error"] = "ok"
    message: str | None = None
    data: DataT | None = None
    # 两个重载：
    # 1) 调用者传入具体的 DataT，返回 Response[DataT]
    @overload
    @classmethod
    def ok(cls, data: DataT, message: str | None = "ok") -> Response[DataT]:
        ...

    # 2) 调用者使用 kwargs 构建匿名 dict 数据，返回 Response[dict[str, Any]]
    @overload
    @classmethod
    def ok(cls, data: None = None, message: str | None = "ok", **data_fields: Any) -> Response[dict[str, Any]]:
        ...

    @classmethod
    def ok(cls, data: Any | None = None, message: str | None = "ok", **data_fields: Any) -> Response[dict[str, Any]] | Response[DataT]:
        """创建一个成功响应（OK）。

        使用方式示例：
        - Response[LoginResponse].ok(LoginResponse(...))
        - Response[LoginResponse].ok({"username":..., "token": ...})
        - Response[LoginResponse].ok(username=..., token=...)
        """
        if data is None and data_fields:
            # 如果传入 kwargs，则把它们当作一个简单的 dict 作为 data
            data = dict(data_fields)
        return cls(status="ok", message=message, data=data)

    @classmethod
    def error(cls, message: str | None = "error") -> Self:
        return cls(status="error", message=message, data=None)
    
    @staticmethod
    def sse(stream: AsyncIterable[str], headers: dict[str, str] | None = None) -> StreamingResponse:
        """
        用于返回标准 SSE 响应。
        stream: async 生成器，yield 每条 data: ...\n\n
        headers: 可选自定义响应头（如 Content-Type、Cache-Control 等）
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
    
#region 日志消息模型


    
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