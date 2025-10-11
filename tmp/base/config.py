from __future__ import annotations
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import ClassVar, Optional
import toml
import logging

__all__ = ["AstrbotConfig"]

logger = logging.getLogger("AstrbotCanary.Config")

class AstrbotConfig(BaseSettings):
    """Astrbot 配置类
    使用 pydantic 进行配置管理
    """
    # 验证默认值
    model_config = SettingsConfigDict(
        validate_default=True,
        env_nested_delimiter='_', env_nested_max_split=1, env_prefix='ASTRBOT_'
    )
    # `_instance` should be a plain class variable, not a pydantic model field.
    # Declare it as `ClassVar[...]` so pydantic won't treat it as a model attribute.
    _instance: ClassVar[Optional["AstrbotConfig"]] = None
    # ASTRBOT_ROOT --> root
    # ASTRBOT_LOG_LEVEL --> log.level
    # ASTRBOT_xxx_xxx --> xxx.xxx ...
    # 因为：env_nested_max_split=1
    # 所以：
    # ASTRBOT_xxx_YYY_ZZZ --> xxx.YYY_ZZZ ...

    ROOT : Path = Field(default=Path.home() / ".astrbot", description="Astrbot 根目录")
    webroot : Path = Field(default=Path.cwd() / "astrbot" / "webroot", description="Web 前端文件夹路径 默认在当前目录的 astrbot/webroot 下.")

    @classmethod
    def getConfig(cls) -> AstrbotConfig:
        """
        供模块使用，插件使用的API由插件加载器提供，不由BASE模块提供
        """
        if cls._instance is None:
            logger.info("创建元数据")
            cls._instance = cls()
            cls._instance.ROOT.mkdir(parents=True, exist_ok=True)
        
            # 如果有配置文件，则加载配置文件
            cls._instance.sync()

        return cls._instance

    def save(self,path: Path | None = None):
        """
        保存配置到文件
        """
        _json = self.model_dump()
        if path is None:
            path = self.ROOT / "metadata.toml"
        toml.dump(_json, path.open("w", encoding="utf-8"))

    def sync(self):
        if self.ROOT / "metadata.toml":
            try:
                _metadata = toml.load((self.ROOT / "metadata.toml").open("r", encoding="utf-8"))
            except Exception as e:
                logger.error(f"格式错误，终止同步: {e}")
                return
            try:
                synced_config = self.model_validate(_metadata)
                AstrbotConfig._instance = synced_config
            except Exception as e:
                logger.error(f"类型错误，终止同步: {e}")


if __name__ == "__main__":
    # 设置环境变量ASTRBOT_ROOT 为 "C:/test/astrbot"
    
    config = AstrbotConfig()
    print(config)
    print("Config ROOT:", config.ROOT)
    config.webroot = Path("C:/test/astrbot3")
    
    print("Modified webroot:", config.webroot)
    config.save()
    import time
    # 这里等待5秒钟，方便手动修改配置文件测试
    time.sleep(5)

    config2: AstrbotConfig = AstrbotConfig.getConfig()

    print("Reloaded:", config2)

    # from annotationlib import Format, call_annotate_function, get_annotate_from_class_namespace
