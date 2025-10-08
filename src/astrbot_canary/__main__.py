# 安装错误堆栈追踪器
from importlib.metadata import EntryPoint
import logging
import sys
import rich.traceback

from astrbot_canary.base import AstrbotBaseModule,Utils

rich.traceback.install()
logger = logging.getLogger("astrbot_canary.loader")

Utils.set_logging_basic_config(logging.INFO)

def main(LoaderName: str = "canary_loader", LoaderArgs: list[str] = ["astrbot.modules.core.canary_eventbus","astrbot.modules.web.canary_web"]):
    """
    LoaderArgs : 加载器参数
    作用，加载器将按照此顺序加载入口点定义的模块
    例如：["astrbot.modules.core.canary_eventbus","astrbot.modules.web.canary_web"]
    将按此顺序加载canary版本的事件总线和Web模块
    
    """
    from astrbot_canary.base import Utils

    AstrbotLoaderCls: EntryPoint | None = Utils.load_from_entrypoint("astrbot.modules.loader", LoaderName)

    if AstrbotLoaderCls is None:
        raise RuntimeError(f"Cannot find AstrbotLoader entry point '{LoaderName}' in group 'astrbot.modules.loader'\n try: uv pip install -e .")

    AstrbotLoader: AstrbotBaseModule = AstrbotLoaderCls.load()()
    logger.info(f"Using AstrbotLoader: {LoaderName}")
    # 初始化加载器
    AstrbotLoader.Awake()

    # 启动加载器
    AstrbotLoader.Start(LoaderArgs)

if __name__ == "__main__":
    _loaderName = sys.argv[1] if len(sys.argv) > 1 else "canary_loader"
    _loaderArgs = sys.argv[2:] if len(sys.argv) > 2 else ["astrbot.modules.core.canary_eventbus","astrbot.modules.web.canary_web"]
    main(LoaderName=_loaderName, LoaderArgs=_loaderArgs)