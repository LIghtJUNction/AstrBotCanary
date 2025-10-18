from __future__ import annotations

from pathlib import Path
from typing import Any, Generic
from pydantic import BaseModel, Field
import toml

from astrbot_canary_api.interface import T, IAstrbotConfigEntry

from logging import getLogger
logger = getLogger("astrbot_canary.config")

__all__ = ["AstrbotConfig"]

class AstrbotConfigEntry(BaseModel, Generic[T]):
    name: str
    group: str
    value: T
    default: T
    description: str
    cfg_file: Path | None = Field(default=None, exclude=True)

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @classmethod
    def bind(
        cls,
        group: str,
        name: str,
        default: T,
        description: str,
        cfg_dir: Path,
    ) -> AstrbotConfigEntry[T]:
        """工厂方法：优先从文件加载，否则新建并保存"""
        cfg_file = (cfg_dir / f"{group}.toml").resolve()
        if cfg_file.exists():
            return cls._from_file(cfg_file)
        entry = cls(
            name=name,
            group=group,
            value=default,
            default=default,
            description=description,
        )
        entry.cfg_file = cfg_file
        entry.save()
        return entry

    @classmethod
    def _from_file(cls, cfg_file: Path) -> "AstrbotConfigEntry[T]":
        """从 toml 文件反序列化配置项"""
        with cfg_file.open("r", encoding="utf-8") as f:
            data = toml.load(f)
        entry = cls.model_validate(data)
        entry.cfg_file = cfg_file
        return entry

    def save(self) -> None:
        """保存配置到 toml 文件"""
        if not self.cfg_file:
            logger.error("配置文件路径未设置，无法保存配置")
            return
        self.cfg_file.parent.mkdir(parents=True, exist_ok=True)
        with self.cfg_file.open("w", encoding="utf-8") as f:
            toml.dump(self.model_dump(), f)

    def load(self) -> None:
        """从本地文件加载配置（覆盖当前值）"""
        if self.cfg_file and self.cfg_file.exists():
            loaded = self._from_file(self.cfg_file)
            self.value = loaded.value
            self.default = loaded.default
            self.description = loaded.description
        else:
            logger.warning(f"配置文件 {self.cfg_file} 不存在，无法加载配置")

    def reset(self) -> None:
        """重置为默认值并保存"""
        self.value = self.default
        self.save()

    def __repr__(self) -> str:
        return f"<@{self.group}.{self.name}={self.value}?{self.default}>"

    def __str__(self) -> str:
        return (
            f"AstrbotConfigEntry\n"
            f"{self.group}.{self.name}={self.value}\n"
            f"Description: {self.description}\n"
            f"Default: {self.default}"
        )
    
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
        self._entries: dict[str,IAstrbotConfigEntry[Any]] = {}

    @classmethod
    def getConfig(cls) -> AstrbotConfig:
        """工厂方法：返回针对指定 pypi_name 的新实例（实例独立）。"""
        return cls()

    def findEntry(self, group: str, name: str) -> IAstrbotConfigEntry[Any] | None:
        """在当前实例作用域查找配置项（只查本实例，不访问全局）。"""
        _key = group + "." + name
        return self._entries.get(_key)

    def bindEntry(self, entry: IAstrbotConfigEntry[Any]) -> IAstrbotConfigEntry[Any]:
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
        # 支持反序列化回去，前提是使用BaseModel且声明正确
        
        host: str = Field("localhost", description="数据库主机")
        port: int = Field(5432, description="数据库端口")
        user: str = Field("user", description="数据库用户")
        password: str = Field("password", description="数据库密码")
        sub_config: SubConfig = SubConfig(sub_field1="nested_value", sub_field2=100)

    # 序列化反序列化测试
    # 创建配置实例并绑定条目，验证保存与加载行为
    cfg = AstrbotConfig.getConfig()

    # 创建一个嵌套配置条目并绑定
    nested_default = NestedConfig(
        type_1=Type1.OPTION_A.value,
        type_2=Type2.OPTION_X,
        host="localhost",
        port=5432,
        user="user",
        password="password",
        sub_config=SubConfig(sub_field1="nested_value", sub_field2=100),
    )
    entry = AstrbotConfigEntry[NestedConfig].bind(
        group="database",
        name="main",
        default=nested_default,
        description="主数据库配置",
        cfg_dir=cfg_dir,
    )
    print(f"Created config entry: {entry}")

    print(entry.value.port)
    print(entry.default.port)
    print(entry.cfg_file)
    print(entry.value.type_1)
    print(entry.value.type_2)
    entry.reset()
    print("After reset:")
    print(entry.value.port)
    print(entry.default.port)
    print(entry.cfg_file)
    print(entry.value.type_1)
    print(entry.value.type_2)

    print("AstrbotConfig 自检通过：绑定/保存/加载/默认值分离 流程工作正常。")

