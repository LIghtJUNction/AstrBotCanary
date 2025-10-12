from importlib.metadata import EntryPoint, EntryPoints
from pathlib import Path

from pydantic import BaseModel, Field

from astrbot_canary_api import (
    IAstrbotModule, 
    IAstrbotConfigEntry ,
    IAstrbotPaths,
    AstrbotPaths , 
    AstrbotConfig , 
    AstrbotConfigEntry 
)
from click import confirm, prompt

from logging import getLogger

from astrbot_canary_api.enum import AstrBotModuleType
from astrbot_canary_helper import AstrbotCanaryHelper

# 类型字典

type module_info = dict[str, tuple[str, str, str ]]
"""pypi_name :(module_type, group, name)"""

type module_load_result = dict[str, tuple[str, str, str , bool]]
"""pypi_name :(module_type, group, name, success)"""


class AstrbotModuleConfig(BaseModel):
    """模块配置，保存已加载的模块列表等"""
    last_loaded_modules: module_info = Field(default_factory=dict[str, tuple[str, str, str]] )
    # pypi_name, (module_type , group, name , #后续新增 bool 表示是否加载成功)
    loader: list[tuple[str, str]] = Field(..., description="全部已发现loader模块 (group, name)")
    web: list[tuple[str, str]] = Field(..., description="全部已发现web模块 (group, name)")
    tui: list[tuple[str, str]] = Field(..., description="全部已发现tui模块 (group, name)")

logger = getLogger("astrbot_canary.module.core")

class AstrbotCoreModule(IAstrbotModule):
    name = "canary_core"
    pypi_name = "astrbot_canary"
    module_type = AstrBotModuleType.CORE
    version = "1.0.0"
    authors = ["LIghtJUNction"]
    description = "Core module for Astrbot Canary."
    enabled = True

    def Awake(self) -> None:
        logger.info(f"{self.name} v{self.version} is awakening.")
        # 初始化Paths和Config
        self.paths: IAstrbotPaths = AstrbotPaths.root(self.pypi_name)
        if self.paths.astrbot_root == Path.home() / ".astrbot":
            if not confirm("你确定要使用推荐的默认路径~/.astrbot 吗？", default=True):
                custom_astrbot_root_str: str = prompt("请输入你想要的路径（直接回车将使用当前路径）",default=".")
                custom_astrbot_root = Path(custom_astrbot_root_str).expanduser().resolve()
                # 非空目录警告
                logger.info(f"你选择的路径是 {custom_astrbot_root}")
                if any(custom_astrbot_root.iterdir()):
                    if not confirm(f"你确定要使用非空目录 {custom_astrbot_root} 吗？", default=False):
                        logger.info("操作已取消。")
                        exit(0)

                self.paths.astrbot_root = custom_astrbot_root

        logger.info(f"使用的 Astrbot 根目录是 {self.paths.astrbot_root}")
        self.config: AstrbotConfig = AstrbotConfig.getConfig(self.pypi_name)

        # 绑定配置
        self.cfg_webroot: IAstrbotConfigEntry = self.config.bindEntry(
            entry=AstrbotConfigEntry.bind(
                pypi_name=self.pypi_name,
                group="metadata",
                name="webroot",
                default=self.paths.astrbot_root / "webroot",
                description="webroot directory",
                config_dir=self.paths.config
            )
        )

        # 上次启动配置
        self.cfg_modules: IAstrbotConfigEntry = self.config.bindEntry(
            entry=AstrbotConfigEntry.bind(
                pypi_name=self.pypi_name,
                group="core",
                name="last_loaded_modules",
                default=AstrbotModuleConfig(loader=[("astrbot.modules.loader","canary_loader")], web=[("astrbot.modules.web","canary_web")], tui=[("astrbot.modules.tui","canary_tui")]),
                description="List of modules loaded in the last session",
                config_dir=self.paths.config
            )
        )

        logger.debug(self.cfg_webroot)
    # 开始自检 -- 尝试从入口点发现loader模块和frontend模块
    def Start(self) -> None:
        # 发现所有入口点并输出日志
  
        loaders: EntryPoints = AstrbotCanaryHelper.getAllEntryPoints(group="astrbot.modules.loader")
        webs: EntryPoints = AstrbotCanaryHelper.getAllEntryPoints(group="astrbot.modules.web")
        tuis: EntryPoints = AstrbotCanaryHelper.getAllEntryPoints(group="astrbot.modules.tui")

        logger.info(f"发现的 loader 入口点: {[ (ep.name, getattr(ep, 'group', None)) for ep in loaders ]}")
        logger.info(f"发现的 web 入口点: {[ (ep.name, getattr(ep, 'group', None)) for ep in webs ]}")
        logger.info(f"发现的 tui 入口点: {[ (ep.name, getattr(ep, 'group', None)) for ep in tuis ]}")
        logger.info(f"{self.name} v{self.version} has started.")
        # 优先加载上次记录的模块
        last_modules: dict[str, tuple[str, str, str]] = self.cfg_modules.value.last_loaded_modules
        logger.info(f"last_modules: {last_modules}")
        if last_modules:
            logger.info(f"上次启动时加载的模块有：{last_modules}")
            if confirm("是否直接加载这些模块？", default=True):
                result: module_load_result = self.load_last_modules(last_modules)
                logger.info(f"模块加载完成，加载结果：{result}")
                return
        # 没有记录或加载失败，自动发现并更新配置
        modules: EntryPoints = self.find_modules()

        result = self.load_modules(modules)

        self.update_cfg_modules(result, self.cfg_modules)

        logger.info(f"模块加载完成，加载结果：{result}")
        
    def OnDestroy(self) -> None:
        logger.info(f"{self.name} v{self.version} is being destroyed.")

    def load_last_modules(self, last_modules: dict[str, tuple[str, str, str]]) -> module_load_result:
        """ 返回加载结果字典 """
        result: module_load_result = {}
        for pypi_name, (module_type_str, group, name) in last_modules.items():
            ep = AstrbotCanaryHelper.getSingleEntryPoint(group=group, name=name)
            if not ep:
                logger.warning(f"无法找到上次记录的模块入口点 {group}:{name}，跳过加载。")
                result[pypi_name] = (module_type_str, group, name, False)
                continue
            success: bool = self.load_module(ep)
            logger.info(f"加载上次记录的模块 {group}:{name} {'成功' if success else '失败'}")
            result[pypi_name] = (module_type_str, group, name, success)
        return result

    def load_module(self, entry: EntryPoint) -> bool:
        """尝试加载指定组和名字的模块 -- 返回是否成功"""
        # 实例化
        module_cls: type[IAstrbotModule] = entry.load()
        module_instance: IAstrbotModule = module_cls()
        try:
            module_instance.Awake()
        except Exception as e:
            logger.error(f"模块 {entry.name} 初始化失败: {e}")
            return False
        return True

    def find_modules(self) -> EntryPoints:
        # 发现所有入口点并输出日志
        loaders: EntryPoints = AstrbotCanaryHelper.getAllEntryPoints(group="astrbot.modules.loader")
        webs: EntryPoints = AstrbotCanaryHelper.getAllEntryPoints(group="astrbot.modules.web")
        tuis: EntryPoints = AstrbotCanaryHelper.getAllEntryPoints(group="astrbot.modules.tui")
        logger.info(f"发现的 loader 入口点: {[ (ep.name, getattr(ep, 'group', None)) for ep in loaders ]}")
        # 合并输出
        return AstrbotCanaryHelper.mergeEntryPoints(loaders, webs, tuis)

    def load_modules(self, modules: EntryPoints) -> module_load_result:
        result: module_load_result = {}
        for entry in modules:
            try:
                module_cls = entry.load()
                module_instance: IAstrbotModule = module_cls()
                module_instance.Awake()
                pypi_name: str = module_instance.pypi_name
                result[pypi_name] = (module_instance.module_type.value , entry.group , entry.name, True)
                logger.info(f"模块 {entry.name} 加载成功。")
            except Exception as e:
                result["ERROR"] = (AstrBotModuleType.UNKNOWN.value, entry.group, entry.name, False)
                logger.error(f"模块 {entry.name} 加载失败: {e}")
        return result

    def update_cfg_modules(self, load_result: module_load_result, cfg_modules: IAstrbotConfigEntry) -> None:
        # 保存真实的 (group, name) 信息到 last_loaded_modules
        last_loaded_modules: dict[str, tuple[str, str, str]] = {}
        loader: list[tuple[str, str]] = []
        web: list[tuple[str, str]] = []
        tui: list[tuple[str, str]] = []
        for pypi_name, (module_type_str, group, name, success) in load_result.items():
            if not success:
                continue
            # 直接用解包后的值
            if module_type_str == AstrBotModuleType.LOADER.value:
                loader.append((group, name))
            elif module_type_str == AstrBotModuleType.WEB.value:
                web.append((group, name))
            elif module_type_str == AstrBotModuleType.TUI.value:
                tui.append((group, name))
            last_loaded_modules[pypi_name] = (module_type_str, group, name)
        # 循环结束后再创建和保存配置
        cfg_obj = AstrbotModuleConfig(
            last_loaded_modules=last_loaded_modules,
            loader=loader if loader else cfg_modules.value.loader,
            web=web if web else cfg_modules.value.web,
            tui=tui if tui else cfg_modules.value.tui
        )
        cfg_modules.value = cfg_obj
        cfg_modules.save(self.paths.config)
        logger.info(f"已更新模块配置: {cfg_modules.value}")
