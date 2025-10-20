"""
1. 第一次登录无需默认账密
2. 密码由md5改为sha256 ,并且加盐存储在数据库
"""

from __future__ import annotations

import logging

from astrbot_canary_api.decorators import AstrbotInjector
from astrbot_canary_api.interface import IAstrbotDatabase
from astrbot_canary_web.models import Base, Response, User
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

logger = logging.getLogger("astrbot.module.auth")

__all__ = ["auth_router"]

auth_router: APIRouter = APIRouter(prefix="/auth", tags=["Auth"])


class LoginResponse(BaseModel):
    username: str | None = None
    token: str | None = None
    change_pwd_hint: bool = False
    """ 我将逻辑改成了：首次登录时接受任意账号密码并写入数据库作为默认用户。
    之后的登录才需要验证密码（数据库不为空）
    默认密码 和默认密码我给移除了
    如果检测到使用默认密码登录
    则返回 change_pwd_hint=True 提示前端要求用户修改密码。
    并告知用户：
    1. 第一次登录无需默认账密
    """


@auth_router.post("/login")
async def login(request: Request) -> Response[LoginResponse]:
    logger.info(
        f"[login] request from {request.client.host if hasattr(request, 'client') and request.client else 'unknown'}",
    )

    data = await request.json()
    username = data.get("username")
    password = data.get("password")
    logger.info(f"Received login attempt for username: {username}")
    db: IAstrbotDatabase = AstrbotInjector.get("CANARY_WEB_DB")
    # 初始化表结构
    db.bind_base(Base)

    JWT_EXP_DAYS: int = AstrbotInjector.get("JWT_EXP_DAYS")
    # md5(astrbot) = 77b90590a8945a7d36c963981a307dc9
    is_default_password = password == "77b90590a8945a7d36c963981a307dc9"
    # 检测是否使用默认密码登录(不再需要)

    if not username or not password:
        raise HTTPException(status_code=400, detail="必须提供用户名和密码")

    # 使用事务上下文执行 ORM 查询与写入
    try:
        async with db.atransaction() as session:
            # 检查是否有任何用户存在
            result = await session.execute(select(User))
            existing_users = result.scalars().all()

            if len(existing_users) == 0:
                # 首次登录：接受任意账号/密码并写入数据库作为默认用户
                # 使用 User.create_and_issue_token 将创建与 token 签发都封装在模型里
                _result = await User.create_and_issue_token(
                    session=session,
                    username=username,
                    password=password,
                    exp_days=JWT_EXP_DAYS,
                )
                token = _result[1]
                return Response[LoginResponse].ok(
                    message="first user created and logged in",
                    data=LoginResponse(
                        username=username,
                        token=token,
                        change_pwd_hint=is_default_password,
                    ),
                )

            # 非首次：查找指定用户名 (username 为主键，使用 session.get)
            user = await session.get(User, username)
            if not user:
                # 用户不存在 -> 返回错误响应
                return Response[LoginResponse].error(message="未找到用户")

            # 比对密码（使用异步业务方法）
            # 需新增 User 的 verify_password_async 和 issue_token_async 公共方法
            if not await user.verify_password_async(password):
                return Response[LoginResponse].error(message="密码错误")

            token = await user.issue_token_async(exp_days=JWT_EXP_DAYS)
            return Response[LoginResponse].ok(
                message="login successful",
                data=LoginResponse(
                    username=username,
                    token=token,
                    change_pwd_hint=is_default_password,
                ),
            )

    except HTTPException:
        # 让 HTTPException 向上抛出
        raise
    except Exception as e:
        # 其余异常返回 500
        raise HTTPException(status_code=500, detail=str(e))


"""
{
  "password": "string",
  "new_password": "string",
  "new_username": "string"
}

data: None

"""


class EditAccountResponse(BaseModel): ...


@auth_router.post("/account/edit")
async def edit_account(request: Request) -> Response[EditAccountResponse]:
    logger.info(
        f"[edit_account] request from {request.client.host if hasattr(request, 'client') and request.client else 'unknown'}",
    )
    """Change current user's password/username.

    Expects JSON body:
    {
      "password": "string",
      "new_password": "string",
      "new_username": "string" # 可选
    }

    Authentication: Bearer <token> header is required to identify the user (token payload must contain `sub`).
    """
    db: IAstrbotDatabase = AstrbotInjector.get("CANARY_WEB_DB")

    data = await request.json()
    password = data.get("password")
    new_password = data.get("new_password")
    new_username = data.get("new_username")

    if not password:
        raise HTTPException(status_code=400, detail="当前密码为必填项")

    # Get token from Authorization header to identify current user
    auth_header = request.headers.get("authorization") or request.headers.get(
        "Authorization",
    )
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="需要包含 Bearer token 的 Authorization 头",
        )

    token = auth_header.split(None, 1)[1].strip()

    # Identify user by attempting to verify the token against each user's secret.
    # This delegates all cryptographic operations to User.verify_jwt.

    try:
        async with db.atransaction() as session:
            # Delegate token -> user resolution and verification entirely to model
            try:
                user, _payload = await User.find_by_token_async(
                    session,
                    token,
                    expected_iss="AstrBotCanary",
                )
            except LookupError:
                return Response[EditAccountResponse].error(message="无效的令牌")

            # verify current password（异步业务方法）
            if not await user.verify_password_async(password):
                return Response[EditAccountResponse].error(message="当前密码错误")

            # update password
            if new_password:
                # 如果新旧密码一致，告诉用户，不需要更改
                if await user.verify_password_async(new_password):
                    return Response[EditAccountResponse].error(
                        message="新密码与当前密码相同，无需更改",
                    )
                try:
                    await user.update_password_async(session, new_password)
                except Exception:
                    return Response[EditAccountResponse].error(message="更新密码失败")

            # update username (check uniqueness)
            if new_username and new_username != user.username:
                try:
                    await user.update_username_async(session, new_username)
                except ValueError:
                    return Response[EditAccountResponse].error(
                        message="新用户名已被占用",
                    )

            # commit happens on context exit
            return Response[EditAccountResponse].ok(
                message="账户信息更新成功",
                data=EditAccountResponse(),
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
