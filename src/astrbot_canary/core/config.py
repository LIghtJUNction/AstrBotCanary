from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar, Generic

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import toml

from astrbot_canary.core.paths import AstrbotPaths

__all__ = ["AstrbotConfig", "AstrbotConfigEntry", "AstrbotPaths"]

T = TypeVar("T", bound=BaseModel)

class AstrbotConfigEntry(BaseSettings, Generic[T]):
    pypi_name: str = Field(..., description="模块名称")
    group: str = Field(..., description="配置分组")
    name: str = Field(..., description="配置项名称")
    # 运行时使用 BaseModel 以兼容 pydantic 的行为；为静态类型提示使用 TYPE_CHECKING
    value: T = Field(..., description="配置值")
    default: T = Field(..., description="默认值")
    description: str = Field("", description="配置描述")

    @classmethod
    def bind(
        cls,
        pypi_name: str,
        group: str,
        name: str,
        default: T,
        description: str,
        config_dir: Path,
    ) -> AstrbotConfigEntry[T]:

        entry = cls(
            pypi_name=pypi_name,
            group=group,
            name=name,
            value=default,
            default=default,
            description=description
        )
        config_file = config_dir / f"{group}.{name}.toml"
        if config_file.exists():
            entry.load(pypi_name, config_dir)
        else:
            entry.save(config_dir)
        return entry

    def load(self, pypi_name: str, config_dir: Path) -> None:
        """从本地文件加载配置"""
        config_file = config_dir / f"{self.group}.{self.name}.toml"
        if config_file.exists():
            try:
                file_data = toml.load(config_file.open("r", encoding="utf-8"))
                # 用 pydantic 校验和赋值
                from typing import cast
                entry = cast(AstrbotConfigEntry[T], self.model_validate(file_data))
                val: Any = entry.value
    
                try:
                    self.value = self.default.model_validate(val)
                except Exception:
                    self.value = self.default

                self.description = entry.description
            except Exception as e:
                print(f"Error loading config {config_file}: {e}")

    def save(self, config_dir: Path) -> None:
        """将配置保存回本地文件"""
        config_file = config_dir / f"{self.group}.{self.name}.toml"
        # use JSON mode to ensure Enums and nested models are serialized to primitives
        data = self.model_dump(mode="json")
        # 如果 value 是 BaseModel，序列化为 dict（确保使用 json 模式）
        if hasattr(self.value, "model_dump"):
            value_dict = self.value.model_dump(mode="json")
            data["value"] = value_dict
        try:
            toml.dump(data, config_file.open("w", encoding="utf-8"))
        except Exception as e:
            print(f"Error saving config {config_file}: {e}")

    def reset(self, config_dir: Path) -> None:
        """重置配置为默认值并保存"""
        self.value = self.default
        self.save(config_dir)

    def __repr__(self) -> str:
        return f"@{self.pypi_name}:{self.group}.{self.name}={self.value}?{self.default}>"
    
    def __str__(self) -> str:
        return f"AstrbotConfigEntry \n {self.pypi_name}:{self.group}.{self.name}={self.value} \n Description: {self.description} \n Default: {self.default}"

class AstrbotConfig():
    configs: dict[str, dict[str, AstrbotConfigEntry[Any]]] = {}
    _pypi_name: str

    @classmethod
    def getConfig(cls, pypi_name: str) -> AstrbotConfig:
        # 保证每个 pypi_name 都有自己的配置字典
        if pypi_name not in cls.configs:
            cls.configs[pypi_name] = {}
        _config = cls()
        _config._pypi_name = pypi_name
        return _config

    def findEntry(self, group: str, name: str) -> AstrbotConfigEntry[Any] | None:
        # 直接查当前实例对应 pypi_name 的配置分组
        _key = group + "." + name
        return self.configs.get(self._pypi_name, {}).get(_key, None)

    def bindEntry(self, entry: AstrbotConfigEntry[T]) -> AstrbotConfigEntry[T]:
        """绑定一个配置项"""
        if self._pypi_name not in self.configs:
            self.configs[self._pypi_name] = {}
        _key = entry.group + "." + entry.name
        self.configs[self._pypi_name][_key] = entry
        return entry

if __name__ == "__main__":
    # 测试代码
    from astrbot_canary.core.paths import AstrbotPaths
    from enum import Enum


    cfg_dir: Path = AstrbotPaths.root("TEST").config

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

    entry1: AstrbotConfigEntry[NestedConfig] = AstrbotConfigEntry[NestedConfig].bind(
        pypi_name="TEST",
        group="general",
        name="nested_config",
        default=NestedConfig(
            type_1=Type1.OPTION_B.value,
            type_2=Type2.OPTION_Y,
            host="localhost",
            port=5432,
            user="user",
            password="password",
            sub_config=SubConfig(sub_field1="nested_value", sub_field2=100)
        ),
        description="嵌套配置项",
        config_dir=cfg_dir
    )
    print(entry1)

    entry1.save(cfg_dir)


    entry1.load("TEST", cfg_dir)

    # 读取测试
    # 1. 读取枚举类
    type_1: str = entry1.value.type_1
    type_2: Type2 = entry1.value.type_2
    print(f"type_1: {type_1}, type_2: {type_2}")
    # 2. 读取嵌套类
    sub_field1: str = entry1.value.sub_config.sub_field1
    sub_field2: int = entry1.value.sub_config.sub_field2
    print(f"sub_field1: {sub_field1}, sub_field2: {sub_field2}")
    # 3. 读取基本类型
    host: str = entry1.value.host
    port: int = entry1.value.port
    user: str = entry1.value.user
    password: str = entry1.value.password
    print(f"host: {host}, port: {port}, user: {user}, password: {password}")


