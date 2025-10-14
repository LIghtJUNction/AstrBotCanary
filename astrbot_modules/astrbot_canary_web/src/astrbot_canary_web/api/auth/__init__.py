from robyn import SubRouter
from logging import getLogger
from .login import auth_login
from .account.edit import account_edit

__all__ = ["auth_router"]

logger = getLogger("auth")

auth_router = SubRouter(__file__, prefix="/api/auth")

auth_router.add_route(route_type="POST", endpoint="/api/auth/login", handler=auth_login) #type: ignore

auth_router.add_route(route_type="POST", endpoint="/api/auth/account/edit", handler=account_edit) #type: ignore

