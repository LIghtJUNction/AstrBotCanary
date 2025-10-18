from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any, ClassVar, Generic, Literal, Self, TypeVar, overload
from uuid import uuid4
from pydantic import BaseModel, Field
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, declarative_base, mapped_column, Mapped

from jwt import decode, encode # type: ignore
# PyJWT

Base = declarative_base()

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
        return f"<User id={self.id!r} username={self.username!r}>"

    def to_dict(self) -> dict[str, Any]:
        """返回用户的简要序列化表示。

        注意：在生产 API 中不要暴露 password、salt 或 jwt_secret。
        """
        return {"username": self.username}

    def set_password(self, plain: str) -> None:
        """生成随机盐并使用 PBKDF2-HMAC-SHA256 存储密码哈希（hex）。"""
        salt_bytes = secrets.token_bytes(16)
        self.salt = salt_bytes.hex()
        dk = hashlib.pbkdf2_hmac(hash_name=self._HASH_NAME, password=plain.encode(encoding="utf-8"), salt=salt_bytes, iterations=self._HASH_ITERATIONS)
        self.password = dk.hex()

    def verify_password(self, plain: str) -> bool:
        """使用存储的盐和 PBKDF2 验证明文密码是否匹配已保存的哈希。"""
        try:
            salt_bytes = bytes.fromhex(self.salt)
            dk = hashlib.pbkdf2_hmac(hash_name=self._HASH_NAME, password=plain.encode(encoding="utf-8"), salt=salt_bytes, iterations=self._HASH_ITERATIONS)
            return dk.hex() == (self.password or "")
        except Exception:
            return False

    def generate_jwt(self, username: str | None = None, exp: int = 7) -> str:
        # 使用实例用户名优先
        if username is None:
            username = getattr(self, "username", None)
            if username is None:
                raise ValueError("username must be provided or present on User instance")

        if not self.jwt_secret:
            raise ValueError("User.jwt_secret is not set")

        now = datetime.now(timezone.utc)
        payload = {
            "iss": "AstrBot.Canary",
            "sub": "user_auth",
            "aud": username,
            "nbf": now,
            "iat": now,
            "exp": now + timedelta(days=exp),
            "jti": str(uuid4()),
        }

        token = encode(payload, self.jwt_secret, algorithm="HS256")
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return token


    def verify_jwt(self, token: str, expected_iss: str | None = None, expected_aud: str | None = None) -> dict[str, Any]:
        """使用此用户的 `jwt_secret` 验证 JWT。

        成功时返回解码后的 payload（dict）；验证失败时会抛出 PyJWT 的相关异常（例如 ExpiredSignatureError、InvalidTokenError）。
        如果提供了 expected_iss/expected_aud，则会额外校验对应的 claim。
        """
        decode_kwargs: dict[str, Any] = {"algorithms": ["HS256"]}
        # require exp and sub at minimum
        options: dict[str, Any] = {"require": ["exp", "sub"]}
        if expected_iss is not None:
            decode_kwargs["issuer"] = expected_iss
            options["require"].append("iss")
        if expected_aud is not None:
            # PyJWT supports 'audience' parameter to verify 'aud' claim
            decode_kwargs["audience"] = expected_aud
            options["require"].append("aud")

        decode_kwargs.setdefault("options", {}).update(options)

        # This will raise exceptions like ExpiredSignatureError, InvalidTokenError, etc.
        payload = decode(token, self.jwt_secret, **decode_kwargs)
        return payload

    @classmethod
    def from_token(cls, token: str, session: Session, expected_iss: str | None = None) -> "User":
        """根据 token 定位并验证用户。

        操作步骤：
        1. 在模型内对 token 做不验证签名的解析以提取 `sub`。
        2. 使用 `sub`（作为 username 主键）从数据库加载对应用户。
        3. 委托该用户实例的 `verify_jwt` 完成签名/声明校验。

        失败时抛出 ValueError 或 LookupError。
        """


        try:
            unverified = decode(token, options={"verify_signature": False})
        except Exception:
            raise ValueError("invalid token format")

        sub = unverified.get("sub")
        if not sub:
            raise ValueError("token missing subject")

        # username is primary key; use session.get for direct PK lookup
        user = session.get(cls, sub)
        if not user:
            raise LookupError("user not found")

        # delegate signature/claims verification to the instance method
        try:
            user.verify_jwt(token, expected_iss=expected_iss)
        except Exception as e:
            raise ValueError("invalid token") from e

        return user
    # --- 增删改查 CRUD helpers -------------------------------------------------
    #region 增删改查 CRUD
    # --- 增删改查 CRUD helpers -------------------------------------------------
    @classmethod
    async def create(cls, session: AsyncSession, username: str, password: str, jwt_secret: str | None = None) -> "User":
        """创建新用户并设置密码（含随机盐）与 jwt_secret，然后添加到 session。

        如果用户名已存在会抛出 ValueError。调用者负责提交事务。
        """
        exists = await session.get(cls, username)
        if exists:
            raise ValueError("username already exists")

        if jwt_secret is None:
            jwt_secret = secrets.token_hex(32)

        user = cls(username=username, jwt_secret=jwt_secret)
        user.set_password(password)
        session.add(user)
        return user

    @classmethod
    async def create_and_issue_token(cls, session: AsyncSession, username: str, password: str, exp_days: int) -> tuple["User", str]:
        """异步创建用户并返回 (user, jwt_token)。

        创建与 token 签发均在模型内完成，外层调用方无需处理任何密码学细节。
        """
        user = await cls.create(session, username=username, password=password)
        token = user.generate_jwt(username=username, exp=exp_days)
        return user, token

    def issue_token(self, exp_days: int) -> str:
        """为此用户签发 JWT（对 generate_jwt 的封装）。

        将签发操作呈现为单一方法，以避免上层调用低级密码学函数。
        """
        return self.generate_jwt(username=self.username, exp=exp_days)

    @classmethod
    def get_by_username(cls, session: Session, username: str) -> "User | None":
        """返回已存在的用户或 None。"""
        return session.get(cls, username)

    def update_password(self, session: Session, new_password: str) -> None:
        """更新用户密码（负责生成盐和哈希），并把实例加入 session。"""
        self.set_password(new_password)
        session.add(self)

    def update_username(self, session: Session, new_username: str) -> None:
        """修改用户名（先检查唯一性）。如果被占用会抛出 ValueError。"""
        exists = session.get(User, new_username)
        if exists:
            raise ValueError("username already taken")
        self.username = new_username
        session.add(self)

    def delete(self, session: Session) -> None:
        """Delete this user from the database via the provided session."""
        session.delete(self)

    @classmethod
    def find_by_token(cls, session: Session, token: str, expected_iss: str | None = None) -> tuple["User", dict[str, Any]]:
        """根据 token 定位能验证该 token 的用户。

        该方法会在模型内尝试解析 token（不验证签名）获取 aud 并优先按主键查找对应用户，再由该用户执行完整验证。
        如果候选用户验证失败，会回退到对所有用户尝试验证（规模小的部署可接受）。

        成功时返回 (user, payload)，否则抛出 LookupError。
        """
        last_exc: Exception | None = None

        # First attempt (efficient): decode token WITHOUT verifying signature
        # purely to extract the 'aud' (username) to do a PK lookup. This
        # unverified decode is performed inside the model (not in auth layer)
        # and the returned aud is NOT trusted until verify_jwt succeeds below.
        from typing import cast
        try:
            unverified = decode(token, options={"verify_signature": False})
        except Exception:
            unverified = None

        # help static type checker: treat unverified as an optional dict
        unverified = cast(dict[str, Any] | None, unverified)

        if isinstance(unverified, dict):
            aud = cast(str | None, unverified.get("aud"))
            if aud:
                candidate = session.get(cls, aud)
                if candidate:
                    try:
                        payload = candidate.verify_jwt(token, expected_iss=expected_iss, expected_aud=aud)
                        return candidate, payload
                    except Exception as e:
                        # verification failed for candidate; remember exception
                        last_exc = e

        # Fallback: try verifying against every user (safe but O(N))
        for user in session.query(cls).all():
            try:
                payload = user.verify_jwt(token, expected_iss=expected_iss)
                return user, payload
            except Exception as e:
                last_exc = e

        raise LookupError("no user matches token") from last_exc
    
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