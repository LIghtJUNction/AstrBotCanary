import asyncio
from typing import Any
from pydantic import BaseModel
from robyn import Request
from logging import getLogger
import jwt
import secrets
from datetime import datetime, timedelta
from datetime import timezone
from typing import Any

from astrbot_canary_api.interface import IAstrbotDatabase
from astrbot_canary.core.models import User

logger = getLogger("astrbot_canary.module.web.auth.login")


class LoginResponse(BaseModel):
    token: str
    username: str
    change_pwd_hint: bool


def generate_jwt(username: str, jwt_secret: str) -> str:
    payload: dict[str, str | datetime] = {
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    token: str = jwt.encode(payload, jwt_secret, algorithm="HS256")
    return token


async def auth_login(request: Request, global_dependencies: dict[str, Any]) -> dict[str, Any]:
    # 将请求 JSON 转为字符串字典，防止类型不确定
    post_data: dict[str, str] = request.json() # type: ignore

    db: IAstrbotDatabase = global_dependencies["DB"]

    # 读取请求中的用户名/密码（保证为字符串）
    req_username = str(post_data.get("username", "")).strip()
    req_password = str(post_data.get("password", ""))

    # 简单输入验证，提前返回避免创建空用户名
    if not req_username or not req_password:
        await asyncio.sleep(1)
        return {"error": "用户名或密码不完整"}

    # 从数据库按用户名查询用户
    with db.transaction() as session:
        user = session.query(User).filter(User.username == req_username).first()

        if user is None:
            # 如果表为空：把此次用户名/密码作为首个用户创建并直接登录
            any_user = session.query(User).first()
            if any_user is None:
                new_user = User(
                    username=req_username,
                    password=req_password,
                    jwt_secret=secrets.token_urlsafe(32),
                )
                session.add(new_user)
                session.commit()
                user = new_user

    # 如果没有找到匹配的用户，直接返回认证失败（并延迟以防暴力破解）
    if user is None:
        await asyncio.sleep(3)
        return {"error": "用户名或密码错误"}

    # 把 ORM 属性的实际值取出来并显式转换为字符串，避免静态类型将其视为 Column
    db_username = str(user.username)
    db_password = str(user.password)
    db_jwt_secret = str(user.jwt_secret)

    # 简单输入验证
    if not req_username or not req_password:
        # 不暴露过多信息，直接返回错误
        await asyncio.sleep(1)
        return {"error": "用户名或密码不完整"}

    # 验证用户名和密码
    if req_username == db_username and req_password == db_password:
        change_pwd_hint = False
        # 改什么密码，第一个登录的用户直接登录化身默认用户（admin）

        token = generate_jwt(db_username, db_jwt_secret)
        return {
            "token": token,
            "username": db_username,
            "change_pwd_hint": change_pwd_hint,
        }

    await asyncio.sleep(3)
    return {"error": "用户名或密码错误"}