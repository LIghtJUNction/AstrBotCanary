from typing import Any
from robyn import Request


async def account_edit(request: Request, global_dependencies: dict[str, Any]) -> dict[str, Any]:
    # DEMO_MODE 暂时设为 False
    DEMO_MODE = False
    if DEMO_MODE:
        return {"error": "You are not permitted to do this operation in demo mode"}

    post_data = request.json()

    config = global_dependencies.get("CONFIG")
    if not config:
        return {"error": "Config not available"}

    password = config.get("dashboard", {}).get("password")

    if post_data.get("password") != password:
        return {"error": "原密码错误"}

    new_pwd = post_data.get("new_password")
    new_username = post_data.get("new_username")
    if not new_pwd and not new_username:
        return {"error": "新用户名和新密码不能同时为空，你改了个寂寞"}

    if new_pwd:
        config["dashboard"]["password"] = new_pwd
    if new_username:
        config["dashboard"]["username"] = new_username

    # 假设 config 有 save_config 方法
    if hasattr(config, 'save_config'):
        config.save_config()

    return {"message": "修改成功"}