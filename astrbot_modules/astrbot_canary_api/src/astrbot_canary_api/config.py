from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings
import toml

from astrbot_canary_api.interface import IAstrbotConfig, IAstrbotConfigEntry

__all__ = ["AstrbotConfig", "AstrbotConfigEntry"]

class AstrbotConfigEntry(BaseSettings):
    pypi_name: str = Field(..., description="模块名称")
    group: str = Field(..., description="配置分组")
    name: str = Field(..., description="配置项名称")
    value: Any = Field(..., description="配置值")
    default: Any = Field(..., description="默认值")
    description: str = Field("", description="配置描述")

    @classmethod
    def bind(
        cls,
        pypi_name: str,
        group: str,
        name: str,
        default: Any,
        description: str,
        config_dir: Path
    ) -> "AstrbotConfigEntry":
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
                entry = self.model_validate(file_data)
                self.value = entry.value
                self.default = entry.default
                self.description = entry.description
            except Exception as e:
                print(f"Error loading config {config_file}: {e}")


    def save(self, config_dir: Path) -> None:
        """将配置保存回本地文件"""
        config_file = config_dir / f"{self.group}.{self.name}.toml"
        data = self.model_dump()
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

class AstrbotConfig(IAstrbotConfig):
    configs: dict[str, dict[str, IAstrbotConfigEntry]] = {}

    @classmethod
    def getConfig(cls, pypi_name: str) -> "AstrbotConfig":
        # 保证每个 pypi_name 都有自己的配置字典
        if pypi_name not in cls.configs:
            cls.configs[pypi_name] = {}
        _config = cls()
        _config._pypi_name = pypi_name
        return _config

    def findEntry(self, group: str, name: str) -> IAstrbotConfigEntry | None:
        # 直接查当前实例对应 pypi_name 的配置分组
        _key = group + "." + name
        return self.configs.get(self._pypi_name, {}).get(_key, None)
    
    def bindEntry(self, entry: IAstrbotConfigEntry) -> IAstrbotConfigEntry:
        """绑定一个配置项"""
        if self._pypi_name not in self.configs:
            self.configs[self._pypi_name] = {}
        _key = entry.group + "." + entry.name
        self.configs[self._pypi_name][_key] = entry
        return entry

    

if __name__ == "__main__":
    # 测试代码
    from .paths import AstrbotPaths

    config_dir: Path = AstrbotPaths.root(pypi_name="test_module").config
    # ~/.astrbot/config/test_module/

    entry1: AstrbotConfigEntry = AstrbotConfigEntry.bind(
        pypi_name="test_module",
        group="general",
        name="enable_feature",
        default=True,
        description="Enable or disable the feature",
        config_dir=config_dir
    )

    entry2: AstrbotConfigEntry = AstrbotConfigEntry.bind(
        pypi_name="test_module",
        group="general",
        name="max_retries",
        default=5,
        description="Maximum number of retries",
        config_dir=config_dir
    )

    config: AstrbotConfig = AstrbotConfig.getConfig("test_module")

    result: IAstrbotConfigEntry | None = config.findEntry("general", "enable_feature")
    if result is not None:
        print(result.value)
    else:
        print("配置项不存在")

    result2: IAstrbotConfigEntry | None = config.findEntry("general", "max_retries")
    if result2 is not None:
        print(result2.value)
    else:
        print("配置项不存在")


    # 修改配置并保存
    entry1.value = False
    entry1.save(config_dir=config_dir)

    entry2.value = 10
    entry2.save(config_dir=config_dir)
