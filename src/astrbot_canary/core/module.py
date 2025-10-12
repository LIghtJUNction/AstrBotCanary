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

from astrbot_canary_api.enums import AstrBotModuleType
from astrbot_canary_helper import AstrbotCanaryHelper

from astrbot_canary_api.msgbus import AstrbotMessageBus

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
    unknown: list[tuple[str, str]] = Field(..., description="全部已发现unknown模块 (group, name)")


logger = getLogger("astrbot_canary.module.core")

class AstrbotCoreModule(IAstrbotModule):
    name = "canary_core"
    pypi_name = "astrbot_canary"
    module_type = AstrBotModuleType.CORE
    version = "1.0.0"
    authors = ["LIghtJUNction"]
    description = "Core module for Astrbot Canary."
    enabled = True

    loaded_modules: dict[str, IAstrbotModule] = {}
#region 基本生命周期
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

        # 上次启动配置
        self.cfg_modules: IAstrbotConfigEntry = self.config.bindEntry(
            entry=AstrbotConfigEntry.bind(
                pypi_name=self.pypi_name,
                group="core",
                name="last_loaded_modules",
                default=AstrbotModuleConfig(loader=[("astrbot.modules.loader","canary_loader")], web=[("astrbot.modules.web","canary_web")], tui=[("astrbot.modules.tui","canary_tui")], unknown=[("","")]),
                description="List of modules loaded in the last session",
                config_dir=self.paths.config
            )
        )
        # 启动消息总线 -- 内存传输器（memory://astrbot）
        self.msgbus: AstrbotMessageBus = AstrbotMessageBus.getBus("memory://astrbot")

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
        last_modules: module_info = self.cfg_modules.value.last_loaded_modules
        
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

        logger.info(f"模块唤醒完成，加载结果：{result}")

        logger.info(f"已加载的模块有：{list(self.loaded_modules.keys())}")

        # 启动模块Start
        for module in self.loaded_modules.values():
            try:
                module.Start()
            except Exception as e:
                logger.error(f"模块 {module.name} 启动失败: {e}")
        
        
    def OnDestroy(self) -> None:
        logger.info(f"{self.name} v{self.version} is being destroyed.")
        self.cfg_modules.save(self.paths.config)
        AstrbotMessageBus.resetBus()
#endregion


#region 模块加载相关
    def load_last_modules(self, last_modules: module_info) -> module_load_result:
        """ 返回加载结果字典 """
        result: module_load_result = {}
        for pypi_name, (module_type_str, group, name) in last_modules.items():
            ep = AstrbotCanaryHelper.getSingleEntryPoint(group=group, name=name)
            if not ep:
                logger.warning(f"无法找到上次记录的模块入口点 {group}:{name}，跳过加载。")
                result[pypi_name] = (module_type_str, group, name, False)
                continue
            _, success = self.load_module(ep)

            logger.info(f"加载上次记录的模块 {group}:{name} {'成功' if success else '失败'}")
            result[pypi_name] = (module_type_str, group, name, success)
        return result

    def load_module(self, entry: EntryPoint) -> tuple[IAstrbotModule | None, bool]:
        """尝试加载指定组和名字的模块 -- 返回是否成功"""
        # 实例化
        module_cls: type[IAstrbotModule] = entry.load()
        module_instance: IAstrbotModule = module_cls()
        try:
            module_instance.Awake()
            
        except Exception as e:
            logger.error(f"模块 {entry.name} 初始化失败: {e}")
            return None, False
        
        self.loaded_modules[module_instance.pypi_name] = module_instance
        return module_instance, True

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
        # 按类型分组
        grouped: dict[str, list[EntryPoint]] = {
            AstrBotModuleType.LOADER.value: [],
            AstrBotModuleType.WEB.value: [],
            AstrBotModuleType.TUI.value: [],
            AstrBotModuleType.UNKNOWN.value: []
        }
        for module_ep in modules:
            module: type[IAstrbotModule] = module_ep.load()
            module_type: str = module.module_type.value
            match module_type:
                case "loader":
                    grouped[AstrBotModuleType.LOADER.value].append(module_ep)
                case "web":
                    grouped[AstrBotModuleType.WEB.value].append(module_ep)
                case "tui":
                    grouped[AstrBotModuleType.TUI.value].append(module_ep)
                case _:
                    grouped[AstrBotModuleType.UNKNOWN.value].append(module_ep)
                    logger.warning(f"发现未知类型的模块入口点 {module_ep.name}，归类为 unknown。")

        # loader只允许选一个
        selected_loader = None
        if len(grouped[AstrBotModuleType.LOADER.value]) > 1:
            loader_names = [f"{i}: {ep.name}" for i, ep in enumerate(grouped[AstrBotModuleType.LOADER.value])]
            idx = prompt(
                "发现多个 loader 模块，请输入要加载的序号（仅允许单选）：\n" +
                "\n".join(loader_names),
                default="0"
            )
            try:
                idx = int(idx)
                selected_loader = grouped[AstrBotModuleType.LOADER.value][idx] if 0 <= idx < len(grouped[AstrBotModuleType.LOADER.value]) else grouped[AstrBotModuleType.LOADER.value][0]
            except Exception:
                logger.warning("输入有误，默认只加载第一个 loader。")
                selected_loader = grouped[AstrBotModuleType.LOADER.value][0]
        elif grouped[AstrBotModuleType.LOADER.value]:
            selected_loader = grouped[AstrBotModuleType.LOADER.value][0]

        # web/tui/unknown三组加起来只能选一个
        ui_candidates = (
            grouped[AstrBotModuleType.WEB.value] +
            grouped[AstrBotModuleType.TUI.value] +
            grouped[AstrBotModuleType.UNKNOWN.value]
        )
        selected_ui = None
        if len(ui_candidates) > 1:
            ui_names = [f"{i}: {ep.name} ({getattr(ep, 'group', '')})" for i, ep in enumerate(ui_candidates)]
            idx = prompt(
                "发现多个 UI(web/tui/unknown) 模块，请输入要加载的序号（仅允许单选）：\n" +
                "\n".join(ui_names),
                default="0"
            )
            try:
                idx = int(idx)
                selected_ui = ui_candidates[idx] if 0 <= idx < len(ui_candidates) else ui_candidates[0]
            except Exception:
                logger.warning("输入有误，默认只加载第一个 UI。")
                selected_ui = ui_candidates[0]
        elif ui_candidates:
            selected_ui = ui_candidates[0]

        # 只加载用户选择的模块，其余同类模块设置为加载失败
        to_load: list[EntryPoint] = []
        if selected_loader:
            to_load.append(selected_loader)
        if selected_ui:
            to_load.append(selected_ui)

        loaded_names = set(ep.name for ep in to_load)

        # 按优先级顺序加载
        for type_value in [AstrBotModuleType.LOADER.value, AstrBotModuleType.WEB.value, AstrBotModuleType.TUI.value, AstrBotModuleType.UNKNOWN.value]:
            for entry in grouped[type_value]:
                if entry.name not in loaded_names:
                    # 未被选中，直接标记为加载失败
                    result[entry.name] = (type_value, entry.group, entry.name, False)
                    continue
                module_instance, success = self.load_module(entry)
                pypi_name: str = getattr(module_instance, "pypi_name", entry.name) if module_instance else entry.name
                result[pypi_name] = (type_value, entry.group, entry.name, success)
                if success and module_instance is not None:
                    logger.info(f"模块 {entry.name} 加载成功。")
                else:
                    logger.error(f"模块 {entry.name} 加载失败。")
        return result
#endregion

#region 配置更新相关
    def update_cfg_modules(self, load_result: module_load_result, cfg_modules: IAstrbotConfigEntry) -> None:
        # 保存真实的 (group, name) 信息到 last_loaded_modules
        last_loaded_modules: dict[str, tuple[str, str, str]] = {}
        loader: list[tuple[str, str]] = []
        web: list[tuple[str, str]] = []
        tui: list[tuple[str, str]] = []
        unknown : list[tuple[str, str]] = []
        for pypi_name, (module_type_str, group, name, success) in load_result.items():
            if not success:
                continue
            # 直接用解包后的值
            match module_type_str:
                case AstrBotModuleType.LOADER.value:
                    loader.append((group, name))
                case AstrBotModuleType.WEB.value:
                    web.append((group, name))
                case AstrBotModuleType.TUI.value:
                    tui.append((group, name))
                case AstrBotModuleType.UNKNOWN.value:
                    unknown.append((group, name))
                case _:
                    """ ??????? """
                    logger.error(f"请检查代码逻辑是否有误！ module_type_str: {module_type_str} 不在已知类型中")
                    unknown.append((group, name))

            last_loaded_modules[pypi_name] = (module_type_str, group, name)

        # 循环结束后再创建和保存配置
        cfg_obj = AstrbotModuleConfig(
            last_loaded_modules=last_loaded_modules,
            loader=loader if loader else cfg_modules.value.loader,
            web=web if web else cfg_modules.value.web,
            tui=tui if tui else cfg_modules.value.tui,
            unknown= unknown if unknown else cfg_modules.value.unknown,
        )
        cfg_modules.value = cfg_obj
        cfg_modules.save(self.paths.config)
        logger.info(f"已更新模块配置: {cfg_modules.value}")
