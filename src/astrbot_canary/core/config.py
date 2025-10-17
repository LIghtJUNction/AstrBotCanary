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
        self._entries: dict[str, IAstrbotConfig.Entry[Any]] = {}

    class Entry(BaseSettings, Generic[T]):
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
            # ensure configuration directory exists
            cfg_dir.mkdir(parents=True, exist_ok=True)
            # bind file path before any save/load operations
            entry._cfg_file = config_file
            if config_file.exists():
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
    def getConfig(cls) -> IAstrbotConfig:
        """工厂方法：返回针对指定 pypi_name 的新实例（实例独立）。"""
        return cls()

    def findEntry(self, group: str, name: str) -> IAstrbotConfig.Entry[Any] | None:
        """在当前实例作用域查找配置项（只查本实例，不访问全局）。"""
        _key = group + "." + name
        return self._entries.get(_key)

    def bindEntry(self, entry: IAstrbotConfig.Entry[Any]) -> IAstrbotConfig.Entry[Any]:
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
    entry = AstrbotConfig.Entry[NestedConfig].bind(
        group="database",
        name="main",
        default=nested_default,
        description="主数据库配置",
        cfg_dir=cfg_dir,
    )

    # 绑定到配置实例
    bound = cfg.bindEntry(entry)
    assert bound is entry, "bindEntry 应该返回被绑定的条目实例"

    # 查找并断言
    found = cfg.findEntry("database", "main")
    assert found is not None, "findEntry 未找到已绑定的条目"
    assert found.name == "main" and found.group == "database", "找到的条目标识不正确"

    # 修改并保存，然后重新加载以确认持久化
    found.value.host = "127.0.0.1"
    found.save()

    # 重新绑定一个新的实例（模拟进程重启后的读取）
    new_entry = AstrbotConfig.Entry[NestedConfig].bind(
        group="database",
        name="main",
        default=nested_default,
        description="主数据库配置",
        cfg_dir=cfg_dir,
    )

    # 新实例应具有之前保存的值
    assert new_entry.value.host == "127.0.0.1", f"持久化加载失败，期待 host=127.0.0.1，实际 {new_entry.value.host}"
    assert new_entry.value.port == 5432, f"持久化加载失败，期待 port=5432，实际 {new_entry.value.port}"
    assert new_entry.value.sub_config.sub_field1 == "nested_value", f"持久化加载失败，期待 sub_field1=nested_value，实际 {new_entry.value.sub_config.sub_field1}"
    assert new_entry.value.sub_config.sub_field2 == 100, f"持久化加载失败，期待 sub_field2=100，实际 {new_entry.value.sub_config.sub_field2}"
    assert new_entry.value.type_1 == Type1.OPTION_A.value, f"持久化加载失败，期待 type_1={Type1.OPTION_A.value}，实际 {new_entry.value.type_1}"
    assert new_entry.value.type_2 == Type2.OPTION_X, f"持久化加载失败，期待 type_2={Type2.OPTION_X}，实际 {new_entry.value.type_2}"
    assert new_entry.value.user == "user", f"持久化加载失败，期待 user=user，实际 {new_entry.value.user}"
    assert new_entry.value.password == "password", f"持久化加载失败，期待 password=password，实际 {new_entry.value.password}"


    print("AstrbotConfig 自检通过：绑定/保存/加载 流程工作正常。")

