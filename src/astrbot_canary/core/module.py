from pathlib import Path
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


logger = getLogger("astrbot_canary.module.core")

class AstrbotCoreModule(IAstrbotModule):
    name = "canary_core"
    pypi_name = "astrbot_canary"
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
        cfg_webroot: IAstrbotConfigEntry = self.config.bindEntry(
            entry=AstrbotConfigEntry.bind(
                pypi_name=self.pypi_name,
                group="metadata",
                name="webroot",
                default=self.paths.astrbot_root / "webroot",
                description="webroot directory",
                config_dir=self.paths.config
            )
        )

        logger.debug(cfg_webroot)







    def Start(self) -> None:
        logger.info(f"{self.name} v{self.version} has started.")

    def OnDestroy(self) -> None:
        logger.info(f"{self.name} v{self.version} is being destroyed.")