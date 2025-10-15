from pydantic import BaseModel
from astrbot_canary_api.interface import IAstrbotDatabase
from astrbot_canary_web.models import Response
from fastapi import APIRouter, HTTPException, Request
import secrets
import jwt
import datetime
import hmac
import hashlib

from astrbot_canary_web.models import User
from fastapi import HTTPException


def generate_jwt(request: Request, username: str, exp: int = 7, fallback_secret: str | None = None) -> str:
    """Generate a JWT token for username.

    exp: Expiration time in days (default 7 days)

    Priority for secret:
    1. request.state.web_module.config["dashboard"]["jwt_secret"] if present
    2. fallback_secret if provided
    Raises ValueError if no secret available.
    """
    cfg_jwt = None

    secret = cfg_jwt or fallback_secret
    if not secret:
        raise ValueError("JWT secret is not set in the config or fallback")

    payload = {
        "username": username,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=exp),
    }
    token = jwt.encode(payload, secret, algorithm="HS256") #type: ignore

    return token

def _hash_password_hs256(password: str, secret: str) -> str:
    """Hash password using HMAC-SHA256 with secret. Returns hex digest."""
    return hmac.new(secret.encode(), password.encode(), hashlib.sha256).hexdigest()


def _verify_password_hs256(password: str, stored_hash: str, secret: str) -> bool:
    try:
        computed = _hash_password_hs256(password, secret)
        return hmac.compare_digest(computed, stored_hash)
    except Exception:
        return False

__all__ = ["auth_router"]

auth_router: APIRouter = APIRouter(prefix="/auth", tags=["Auth"])

class LoginResponse(BaseModel):
    username: str | None = None
    token: str | None = None

@auth_router.post("/login")
async def login(request: Request) -> Response[LoginResponse]:

    # 本函数依赖注入的 db 实例，用于处理登录逻辑
    web_module = Response.deps.get("MODULE")
    if not web_module:
        return Response[LoginResponse].error(message="数据库连接失败：模块未正确初始化")
    db: IAstrbotDatabase = web_module.db

    data = await request.json()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password are required")

    # 使用事务上下文执行 ORM 查询与写入
    try:
        async with db.atransaction() as session:
            # 检查是否有任何用户存在
            existing_users = session.query(User).all()

            if len(existing_users) == 0:
                # 首次登录：接受任意账号/密码并写入数据库作为默认用户
                # 生成 per-user secret，用于哈希密码和 fallback JWT 签名
                jwt_secret = secrets.token_hex(16)
                hashed_pwd = _hash_password_hs256(password, jwt_secret)
                new_user = User(username=username, password=hashed_pwd, jwt_secret=jwt_secret)
                session.add(new_user)

                # 生成 token
                token = generate_jwt(request=request, username=username, fallback_secret=jwt_secret)
                return Response[LoginResponse].ok(message="first user created and logged in", username=username, token=token)

            # 非首次：查找指定用户名
            user = session.query(User).filter_by(username=username).first()
            if not user:
                # 用户不存在 -> 返回错误响应
                return Response[LoginResponse].error(message="user not found")

            # 比对密码（使用 HMAC-SHA256）
            if not _verify_password_hs256(password, user.password, user.jwt_secret):
                # 密码错误 -> 返回错误响应
                return Response[LoginResponse].error(message="invalid password")

            # 登录成功
            token = generate_jwt(request, username, fallback_secret=user.jwt_secret)
            return Response[LoginResponse].ok(message="login successful", username=username, token=token)

    except HTTPException:
        # 让 HTTPException 向上抛出
        raise
    except Exception as e:
        # 其余异常返回 500
        raise HTTPException(status_code=500, detail=str(e))