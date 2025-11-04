from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, TypeVar

import keyring
import toml
from astrbot_canary_api import IAstrbotConfigEntry
from astrbot_canary_api.exceptions import (
    SecretError,
)
from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator


logger = getLogger("astrbot.module.core.config")

__all__ = ["AstrbotConfigEntry"]

T = TypeVar("T", bound=BaseModel)

class AstrbotConfigEntry(IAstrbotConfigEntry[T], BaseModel):
    # type parameter T is used for value/default
    name: str
    group: str
    value: T
    default: T
    description: str
    cfg_file: Path | None = Field(default=None, exclude=True)

    model_config: ClassVar[ConfigDict] = ConfigDict(
        arbitrary_types_allowed=True,
    )

    @classmethod
    def bind(
        cls,
        group: str,
        name: str,
        default: T,
        description: str,
        cfg_dir: Path,
    ) -> AstrbotConfigEntry[T]:
        """工厂方法:优先从文件加载,否则新建并保存.自动根据default类型推断模型类型."""
        cfg_file: Path = (cfg_dir / f"{group}" / f"{name}.toml").resolve()
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

        value = default.model_copy(deep=True)
        default_copy = default.model_copy(deep=True)

        entry = cls(
            name=name,
            group=group,
            value=value,
            default=default_copy,
            description=description,
        )
        entry.cfg_file = cfg_file
        entry.save()
        return entry

    def save(self) -> None:
        """保存配置到 toml 文件(只用BaseModel标准序列化,Path等类型转为字符串)."""
        if not self.cfg_file:
            logger.error("配置文件路径未设置,无法保存配置")
            return
        self.cfg_file.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump(mode="json")
        with self.cfg_file.open("w", encoding="utf-8") as f:
            _ = toml.dump(data, f)

    def load(self) -> None:
        """从本地文件加载配置(覆盖当前值,只用BaseModel标准反序列化)."""
        if self.cfg_file and self.cfg_file.exists():
            with self.cfg_file.open("r", encoding="utf-8") as f:
                data = toml.load(f)
            loaded = type(self).model_validate(data)
            self.value = loaded.value
            self.default = loaded.default
            self.description = loaded.description
        else:
            logger.warning("配置文件 %s 不存在,无法加载配置", self.cfg_file)

    def reset(self) -> None:
        """重置为默认值并保存."""
        self.value = self.default.model_copy(deep=True)
        self.save()

    def __repr__(self) -> str:
        """REPR."""
        return f"<@{self.group}.{self.name}={self.value}?{self.default}>"

    def __str__(self) -> str:
        return (
            f"AstrbotConfigEntry\n"
            f"{self.group}.{self.name}={self.value}\n"
            f"Description: {self.description}\n"
            f"Default: {self.default}"
        )

# 密钥模型

class AstrbotSecretKey(BaseModel):
    """
    AstrbotSecretKey 描述器,用于安全存储和访问密钥.

    使用 keyring 库将密钥存储在系统安全存储中.

    示例用法:
        class Config(BaseModel):
            secret : AstrbotSecretKey = AstrbotSecretKey("llm-key")
    """
    key_name : str
    service: str = "astrbot"
    key_id : str = "none"
    _secret: str | None = None

    @property
    def secret(self) -> str | None:
        logger.warning("访问 secret 属性将返回 key_id 而非密钥本身,请使用上下文管理器.")
        return self.key_id

    @secret.setter
    def secret(self, value: str | None) -> None:
        if self.key_id == "none":
            self.key_id = f"@{self.service}:{self.key_name}"
        if value:
            keyring.set_password(self.service, self.key_id, value)
        self._secret = value

    @secret.deleter
    def secret(self) -> None:
        if self.key_id:
            keyring.delete_password(self.service, self.key_id)
        self._secret = None
        self.key_id = "none"

    def __str__(self) -> str:
        return (f"<AstrbotSecretKey-{self.key_name}@{self.service}:"
                f"{self.key_name}={self.key_id}>")

    @asynccontextmanager
    async def actx(self) -> AsyncGenerator[str]:
        """异步上下文管理器获取密钥."""
        try:
            if self.key_id == "none":
                raise SecretError
            if self._secret is None:
                self._secret = keyring.get_password(self.service, self.key_id) or ""
            yield self._secret
        finally:
            self._secret = None

    @contextmanager
    def ctx(self) -> Generator[str]:
        """同步上下文管理器获取密钥."""
        try:
            if self.key_id == "none":
                raise SecretError
            if self._secret is None:
                self._secret = keyring.get_password(self.service, self.key_id) or ""
            yield self._secret
        finally:
            self._secret = None

