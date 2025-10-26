"""1. 第一次登录无需默认账密
2. 密码由md5改为sha256 ,并且加盐存储在数据库.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, TypeAdapter
from sqlalchemy import select

from astrbot_canary_web.models import Base, Response, User
from astrbot_injector import AstrbotInjector

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.session import AsyncSession
logger = logging.getLogger("astrbot.module.auth")

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


@auth_router.post("/login")
async def login(request: Request) -> Response[LoginResponse]:
    logger.info(
        "[login] request from %s",
        request.client.host
        if hasattr(request, "client") and request.client
        else "unknown",
    )

    data = LoginRequest.model_validate(await request.json())
    username = data.username
    password = data.password
    logger.info("Received login attempt for username: %s", username)
    db_obj = AstrbotInjector.get("CANARY_WEB_DB")
    db: IAstrbotDatabase | None = (
        db_obj if isinstance(db_obj, IAstrbotDatabase) else None
    )
    if db is None:
        msg = "未发现注入的web数据库实例"
        raise RuntimeError(msg)
    # 初始化表结构
    db.bind_base(Base)

    jwt_exp_obj = AstrbotInjector.get("JWT_EXP_DAYS")
    JWT_EXP_DAYS: int | None = jwt_exp_obj if isinstance(jwt_exp_obj, int) else None
    if JWT_EXP_DAYS is None:
        msg = "未发现注入的JWT配置值."
        raise RuntimeError(msg)

    DEFAULT_PASSWORD_HASH = os.environ.get(
        "ASTRBOT_DEFAULT_PASSWORD_HASH",
        "77b90590a8945a7d36c963981a307dc9",
    )
    is_default_password = password == DEFAULT_PASSWORD_HASH  # 这个是用来抛警告的

    if not username or not password:
        raise HTTPException(status_code=400, detail="必须提供用户名和密码")

    # 使用事务上下文执行 ORM 查询与写入
    try:
        async with db.atransaction() as session:
            # 检查是否有任何用户存在
            result = await session.execute(select(User))
            existing_users = result.scalars().all()

            if len(existing_users) == 0:
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

            # 非首次:查找指定用户名 (username 为主键,使用 session.get)
            user = await session.get(User, username)
            if not user:
                # 用户不存在 -> 返回错误响应
                return Response[LoginResponse].error(message="未找到用户")

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
    except (ValueError, TypeError, RuntimeError) as e:
        # 其余异常返回 500
        raise HTTPException(status_code=500, detail=str(e)) from e


class EditAccountRequest(BaseModel):
    password: str = ""
    new_password: str = ""
    new_username: str = ""


class EditAccountResponse(BaseModel): ...


@auth_router.post("/account/edit")
async def edit_account(request: Request) -> Response[EditAccountResponse]:
    logger.info(
        "[edit_account] request from %s",
        request.client.host
        if hasattr(request, "client") and request.client
        else "unknown",
    )
    db_obj = AstrbotInjector.get("CANARY_WEB_DB")
    db: IAstrbotDatabase | None = (
        db_obj if isinstance(db_obj, IAstrbotDatabase) else None
    )
    if db is None:
        msg = "未发现web模块注入的db实例."
        raise RuntimeError(msg)

    try:
        data = await _get_edit_account_data(request)
        token = _get_bearer_token(request)
        async with db.atransaction() as session:
            user = await _find_user_by_token(session, token)
            if not await user.verify_password_async(data["password"]):
                return Response[EditAccountResponse].error(message="当前密码错误")
            if data["new_password"]:
                if await user.verify_password_async(data["new_password"]):
                    return Response[EditAccountResponse].error(
                        message="新密码与当前密码相同,无需更改",
                    )
                try:
                    await user.update_password_async(session, data["new_password"])
                except (ValueError, TypeError, RuntimeError):
                    return Response[EditAccountResponse].error(message="更新密码失败")
            if data["new_username"] and data["new_username"] != user.username:
                try:
                    await user.update_username_async(session, data["new_username"])
                except ValueError:
                    return Response[EditAccountResponse].error(
                        message="新用户名已被占用",
                    )
            return Response[EditAccountResponse].ok(
                message="账户信息更新成功",
                data=EditAccountResponse(),
            )
    except HTTPException:
        raise
    except (ValueError, TypeError, RuntimeError) as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


async def _get_edit_account_data(request: Request) -> dict[str, str]:
    data = EditAccountRequest.model_validate(await request.json())
    password = data.password
    new_password = data.new_password
    new_username = data.new_username
    if not password:
        raise HTTPException(status_code=400, detail="当前密码为必填项")
    return {
        "password": password,
        "new_password": new_password,
        "new_username": new_username,
    }


def _get_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("authorization") or request.headers.get(
        "Authorization",
    )
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="需要包含 Bearer token 的 Authorization 头",
        )

    return token_type.validate_python(auth_header.split(None, 1)[1].strip())


async def _find_user_by_token(session: AsyncSession, token: str) -> User:
    try:
        user, _payload = await User.find_by_token_async(
            session,
            token,
            expected_iss="AstrBotCanary",
        )
    except LookupError as e:
        raise HTTPException(status_code=401, detail="无效的令牌") from e
    else:
        return user
