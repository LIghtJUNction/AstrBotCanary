"""
title: AstrbotCanary Loader
version: v1.0.0
status: dev
authors: [LIghtJUNction]
owners: [LIghtJUNction]
created: 2025-10-08
updated: 2025-10-08
"""
from importlib.metadata import EntryPoint, EntryPoints

from ..base import AstrbotBaseModule
from .specs import LoaderInfo

from pluggy import PluginManager
from logging import getLogger
from tqdm import tqdm

logger = getLogger("AstrbotCanary.Loader")

class AstrbotLoader(AstrbotBaseModule):
    """
    AstrbotCanary加载器
    """
    LOADER_INFO : LoaderInfo = LoaderInfo(
        Name="AstrbotCanary Loader",
        VersionCode="100",
        Author="LIghtJUNction",
        Description="AstrbotCanary加载器",
    )
    pm : PluginManager

    # 模块类引用字典
    modules: dict[str, AstrbotBaseModule | None] = {}
    # None表示这个模块加载失败，但还是记录下来

    # 模块类路径：类引用

    @classmethod
    def Awake(cls):
        """自身初始化
        """
        logger.info(f"AstrbotLoader Awake: {cls.LOADER_INFO}")
        from .specs import ASTRBOT_CANARY_HOOK_NS
        
        cls.pm = PluginManager(ASTRBOT_CANARY_HOOK_NS)

    @classmethod
    def Start(cls, args: list[str] = ["astrbot.modules.core.canary_eventbus","astrbot.modules.web.canary_web"]):
        """在Awake之后调用
        """
        logger.info(f"AstrbotLoader Start with args: {args}")

        logger.info("*"*5 + " Loading modules " + "*"*5)

        # 进度条
        
        for mod in tqdm(args, desc="Loading modules", unit="module"):
            # 更新进度条
            
            group, name = mod.split(".")[:-1], mod.split(".")[-1]
            cls.modules[mod] = cls.LoadModule(group=group, name=name)
            if cls.modules[mod] is None:
                logger.warning(f"Module {mod} failed to load")

        #endregion
        #region 加载插件
        # 加载所有插件 -- pluggy 注册
        cls.LoadPlugins("astrbot.plugins")
        #endregion


    @classmethod
    def LoadModule(cls, group: str | list[str] = "astrbot.modules.core", name: str = "canary_eventbus") -> AstrbotBaseModule | None:
        """加载指定模块
        """
        from ..base import Utils
        if isinstance(group, list):
            group = ".".join(group)

        ep: EntryPoint | None = Utils.load_from_entrypoint(group, name)
        if ep is None:
            logger.error(f"Cannot find module entry point '{name}' in group '{group}'")
            return
        try:
            module_cls: type = ep.load()
            if not issubclass(module_cls, AstrbotBaseModule):
                logger.error(f"Module '{name}' does not inherit from AstrbotBaseModule")
                return
            module: AstrbotBaseModule = module_cls()
            module.Awake()
            module.Start([])
            logger.info(f"Loaded module: {name} from {ep.value}")
            return module
        except Exception:
            logger.exception(f"Failed to load module: {name} from {ep.value}")
            return

    @classmethod
    def LoadPlugins(cls,group:str = "astrbot.plugins") -> None:
        """加载所有插件
        """
        from .specs import PluginSpec
        cls.pm.add_hookspecs(PluginSpec)
        from importlib.metadata import entry_points
        try:
            eps_all: EntryPoints = entry_points()
            # importlib.metadata.EntryPoints 有 select 方法新接口
            if hasattr(eps_all, "select"):
                eps: EntryPoints = eps_all.select(group=group)
            else:
                eps = entry_points(group=group)
        except Exception:
            logger.exception("entry_points discovery failed")
            return

        # 加载插件 -- 进度条
        for ep in tqdm(eps, desc="Loading plugins", unit="plugin"):
            try:
                plugin = ep.load()
                cls.pm.register(plugin())
                logger.info(f"Loaded plugin: {ep.name} from {ep.value}")
            except Exception:
                logger.exception(f"Failed to load plugin: {ep.name} from {ep.value}")
    

"""加载器模块
实现规范
1. 继承自AstrbotBaseModule
2. 实现Awake和Start方法
3. 在Awake中进行初始化操作
4. 在Start中进行启动操作，接受启动参数LoaderArgs: list[str]
LoaderArgs 规范：
启动器参数为为模块入口点全名列表，加载器将按此顺序加载各个子模块
group+name
例如：
[project.entry-points."astrbot.modules.loader"]
"canary_loader" = "astrbot_canary.loader.loader:AstrbotLoader"

astrbot.modules.loader.canary_loader 表示canary版本的加载器(即本模块本身)

替换指南：
在__main__.py中更换加载器模块仅需提供加载器名字即可
def main(LoaderName: str = "canary_loader", LoaderArgs: list[str] = ["astrbot.modules.core.canary_eventbus","astrbot.modules.web.canary_web"])
第一个参数决定使用什么加载器

第二个参数决定加载器按照什么顺序加载其他模块（替换加载器需要实现具体加载逻辑）

加载器调用时机：
__main__.py中调用AstrbotLoader.Awake()和AstrbotLoader.Start(LoaderArgs)

启动顺序：
紧随主程序启动之后，其他模块插件加载之前

加载器职责：
加载其他模块和加载所有插件

"""