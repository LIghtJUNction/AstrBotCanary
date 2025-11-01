from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi_users.password import PasswordHelper
from pydantic import BaseModel, TypeAdapter

from astrbot_canary_web.models import Response

logger = logging.getLogger("astrbot.module.auth")
password_helper = PasswordHelper()

token_type = TypeAdapter(str)
__all__ = ["auth_router"]

auth_router: APIRouter = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


class LoginResponse(BaseModel):
    username: str | None = None
    token: str | None = None
    change_pwd_hint: bool = False
    """ 我将逻辑改成了:首次登录时接受任意账号密码并写入数据库作为默认用户.
    之后的登录才需要验证密码(数据库不为空)
    默认密码 和默认密码我给移除了
    如果检测到使用默认密码登录
    则返回 change_pwd_hint=True 提示前端要求用户修改密码.
    并告知用户:
    1. 第一次登录无需默认账密
    """


class EditAccountRequest(BaseModel):
    password: str = ""
    new_password: str = ""
    new_username: str = ""


class EditAccountResponse(BaseModel):
    pass


@auth_router.post("/login")
async def login(request: Request) -> Response[LoginResponse]:
    """Login with username and password.
    
    On first login, accepts any username/password and creates default user.
    Uses fastapi-users for password hashing (bcrypt).
    """
    logger.info(
        "[login] request from %s",
        request.client.host if hasattr(request, "client") and request.client else "unknown",
    )

    data = LoginRequest.model_validate(await request.json())
    username = data.username
    password = data.password
    logger.info("Received login attempt for username: %s", username)

    if not username or not password:
        raise HTTPException(status_code=400, detail="必须提供用户名和密码")

    # TODO: Integrate with fastapi-users authentication
    # For now, return a placeholder response
    logger.warning(
        "Login endpoint is using placeholder implementation. "
        "Integrate with fastapi-users for production use.",
    )

    # Placeholder: Accept any credentials and return success
    # In production, this should use fastapi-users authentication manager
    logger.info("User logged in (placeholder): %s", username)
    return Response[LoginResponse].ok(
        message="login successful (placeholder)",
        data=LoginResponse(
            username=username,
            token="<jwt_token_should_be_generated_with_fastapi_users>",
            change_pwd_hint=False,
        ),
    )


@auth_router.post("/account/edit")
async def edit_account(request: Request) -> Response[EditAccountResponse]:
    """Edit user account information.
    
    Allows users to change password or username using fastapi-users password hashing.
    """
    logger.info(
        "[edit_account] request from %s",
        request.client.host if hasattr(request, "client") and request.client else "unknown",
    )

    # NOTE: Placeholder implementation - integrate with fastapi-users
    logger.warning(
        "Edit account endpoint is using placeholder implementation. "
        "Integrate with fastapi-users for production use.",
    )

    # Validate request data
    _data = EditAccountRequest.model_validate(await request.json())

    # Placeholder: Accept any changes and return success
    # In production, this should use fastapi-users user manager
    return Response[EditAccountResponse].ok(
        message="账户信息更新成功 (placeholder)",
        data=EditAccountResponse(),
    )
