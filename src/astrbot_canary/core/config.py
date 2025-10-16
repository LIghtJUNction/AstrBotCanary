from __future__ import annotations

from pathlib import Path
from typing import Any, Generic

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import toml

from astrbot_canary.core.paths import AstrbotPaths
from astrbot_canary_api import IAstrbotConfig
from astrbot_canary_api.interface import T

from logging import getLogger
logger = getLogger("astrbot_canary.config")

__all__ = ["AstrbotConfig"]


class AstrbotConfig:
    """
    每个实例独立维护自己的配置表（不再使用类级全局注册表）。
    使用方式：
      cfg = AstrbotConfig.getConfig("pypi_name")
      entry = AstrbotConfigEntry.bind(...); cfg.bindEntry(entry)
      e = cfg.findEntry("group","name")
    注意：不同地方调用 getConfig(...) 会返回独立实例，若需要共享请在上层通过 DI/容器管理单例。
    """
    def __init__(self) -> None:
    # 实例私有的 entries 字典：key -> AstrbotConfigEntry
        self._entries: dict[str, AstrbotConfig.Entry[Any]] = {}

    class Entry(IAstrbotConfig.Entry[T], BaseSettings, Generic[T]):
        name: str
        group: str
        value: T
        default: T
        description: str
        _cfg_file: Path | None = None
        """ 请使用 bind(...) 方法创建实例 
        将自动按格式： {group}.toml 存储在模块配置目录下
        例如 group="database", name="main"
        同组配置合并保存
        """

        @classmethod
        def bind(
            cls,
            group: str,
            name: str,
            default: T,
            description: str,
            cfg_dir: Path,
        ) -> AstrbotConfig.Entry[T]:

            entry = cls(
                group=group,
                name=name,
                value=default,
                default=default,
                description=description
            )

            config_file: Path = (cfg_dir / f"{group}.toml").resolve()
            if config_file.exists():
                entry._cfg_file = config_file
                entry.load()
            else:
                entry.save()
            return entry

        def load(self) -> None:
            """从本地文件加载配置"""
            if self._cfg_file and self._cfg_file.exists():
                config_file = self._cfg_file
                try:
                    file_data = toml.load(config_file.open("r", encoding="utf-8"))
                    # 用 pydantic 校验和赋值
                    entry = self.model_validate(file_data)
                    val: Any = entry.value
                    try:
                        self.value = self.default.model_validate(val)
                    except Exception:
                        self.value = self.default

                    self.description = entry.description
                except Exception as e:
                    logger.error(f"Error loading config {config_file}: {e}")

        def save(self) -> None:
            """将配置保存回本地文件"""
            if self._cfg_file is None:
                raise ValueError("ConfigEntry not bound to a file. Use bind(...) to create an entry.")
            data = self.model_dump(mode="json")
            value_dict = self.value.model_dump(mode="json")
            data["value"].update(value_dict)
            try:
                toml.dump(data, self._cfg_file.open("w", encoding="utf-8"))
            except Exception as e:
                logger.error(f"Error saving config {self._cfg_file}: {e}")

        def reset(self) -> None:
            """重置配置为默认值并保存"""
            self.value = self.default
            self.save()

        def __repr__(self) -> str:
            return f"<@{self.group}.{self.name}={self.value}?{self.default}>"

        def __str__(self) -> str:
            return f"AstrbotConfigEntry \n {self.group}.{self.name}={self.value} \n Description: {self.description} \n Default: {self.default}"




    @classmethod
    def getConfig(cls) -> AstrbotConfig:
        """工厂方法：返回针对指定 pypi_name 的新实例（实例独立）。"""
        return cls()

    def findEntry(self, group: str, name: str) -> AstrbotConfig.Entry[Any] | None:
        """在当前实例作用域查找配置项（只查本实例，不访问全局）。"""
        _key = group + "." + name
        return self._entries.get(_key)

    def bindEntry(self, entry: AstrbotConfig.Entry[T]) -> AstrbotConfig.Entry[T]:
        """绑定一个配置项到当前实例（覆盖同名项）。"""
        _key = entry.group + "." + entry.name
        self._entries[_key] = entry
        return entry
    


if __name__ == "__main__":
    # 测试代码
    from astrbot_canary.core.paths import AstrbotPaths
    from enum import Enum
    cfg_dir: Path = AstrbotPaths.getPaths("TEST").config
    class SubConfig(BaseModel):
        sub_field1: str = Field("sub_value1", description="子配置字段1")
        sub_field2: int = Field(42, description="子配置字段2")

    class Type1(Enum):
        OPTION_A = "option_a"
        OPTION_B = "option_b"

    class Type2(Enum):
        OPTION_X = "option_x"
        OPTION_Y = "option_y"

    # 测试嵌套配置类
    class NestedConfig(BaseModel):
        type_1: str = Field(Type1.OPTION_A.value, description="类型1选项")
        type_2: Type2 = Field(Type2.OPTION_X, description="类型2选项")
        host: str = Field("localhost", description="数据库主机")
        port: int = Field(5432, description="数据库端口")
        user: str = Field("user", description="数据库用户")
        password: str = Field("password", description="数据库密码")
        sub_config: SubConfig = SubConfig(sub_field1="nested_value", sub_field2=100)

    # 序列化反序列化测试

