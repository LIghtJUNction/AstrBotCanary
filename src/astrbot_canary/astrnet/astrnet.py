from astrbot_canary_api import
class AstrbotNetwork:
    """ Astrbot Taskiq Network: 仿FastAPI风格的taskiq封装
    负责路由分发、中间件管理、异常处理
    """
    scheme: str = "astrbot"