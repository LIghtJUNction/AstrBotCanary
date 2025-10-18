from __future__ import annotations

from pathlib import Path
from typing import Generic
from pydantic import BaseModel, Field
import toml

from astrbot_canary_api.interface import T

from logging import getLogger
logger = getLogger("astrbot_canary.config")

__all__ = ["AstrbotConfigEntry"]

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
        """工厂方法：优先从文件加载，否则新建并保存。自动根据default类型推断模型类型。"""
        cfg_file: Path = (cfg_dir / f"{group}.toml").resolve()
        # 自动推断模型类型
        model_type = type(default)
        if cfg_file.exists():
            with cfg_file.open("r", encoding="utf-8") as f:
                data = toml.load(f)
            # 仅当value/default为dict时才反序列化
            if "value" in data and isinstance(data["value"], dict):
                data["value"] = model_type.model_validate(data["value"])
            if "default" in data and isinstance(data["default"], dict):
                data["default"] = model_type.model_validate(data["default"])
            entry = cls.model_validate(data)
            entry.cfg_file = cfg_file
            return entry
        entry = cls(
            name=name,
            group=group,
            value=default.model_copy(deep=True),
            default=default.model_copy(deep=True),
            description=description,
        )
        entry.cfg_file = cfg_file
        entry.save()
        return entry

    def save(self) -> None:
        """保存配置到 toml 文件（只用BaseModel标准序列化，Path等类型转为字符串）"""
        if not self.cfg_file:
            logger.error("配置文件路径未设置，无法保存配置")
            return
        self.cfg_file.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump(mode="json")
        with self.cfg_file.open("w", encoding="utf-8") as f:
            toml.dump(data, f)

    def load(self) -> None:
        """从本地文件加载配置（覆盖当前值，只用BaseModel标准反序列化）"""
        if self.cfg_file and self.cfg_file.exists():
            with self.cfg_file.open("r", encoding="utf-8") as f:
                data = toml.load(f)
            loaded = type(self).model_validate(data)
            self.value = loaded.value
            self.default = loaded.default
            self.description = loaded.description
        else:
            logger.warning(f"配置文件 {self.cfg_file} 不存在，无法加载配置")

    def reset(self) -> None:
        """重置为默认值并保存"""
        self.value = self.default.model_copy(deep=True)
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
    
    