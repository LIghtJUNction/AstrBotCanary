# Astrbot Config

一个强大的 Python 配置管理库，结合 Pydantic 的类型安全和 keyring 的安全密钥存储。

## 特性

- **类型安全**：使用 Pydantic BaseModel 确保配置数据结构正确
- **自动持久化**：配置自动保存为 TOML 文件
- **安全密钥管理**：敏感信息使用系统密钥环存储，避免明文保存
- **嵌套配置支持**：支持复杂嵌套的配置结构
- **简单 API**：易用的绑定和访问接口

## 安装

```bash
uv pip install astrbot-config

安装到当前项目：
uv add astrbot-config
```

## 快速开始

### 基本配置

```python
from pathlib import Path
from pydantic import BaseModel
from astrbot_canary_config import AstrbotConfigEntry

# 定义配置类
class MyConfig(BaseModel):
    name: str
    value: int

# 绑定配置
cfg = AstrbotConfigEntry[MyConfig].bind(
    group="my_app",
    name="settings",
    default=MyConfig(name="default", value=42),
    description="应用配置",
    cfg_dir=Path.cwd() / "config"
)

# 访问配置
print(cfg.value.name)  # default

# 修改并保存
cfg.value.name = "updated"
cfg.save()
```

### 嵌套配置

```python
class SubConfig(BaseModel):
    enabled: bool
    timeout: int

class AppConfig(BaseModel):
    host: str
    port: int
    features: SubConfig

cfg = AstrbotConfigEntry[AppConfig].bind(
    group="server",
    name="config",
    default=AppConfig(
        host="localhost",
        port=8080,
        features=SubConfig(enabled=True, timeout=30)
    ),
    description="服务器配置",
    cfg_dir=Path.cwd() / "config"
)
```

### 安全密钥管理

```python
from astrbot_canary_config import AstrbotSecretKey
from pydantic import Field

class SecureConfig(BaseModel):
    api_key: AstrbotSecretKey = Field(default_factory=lambda: AstrbotSecretKey(key_name="my-api-key"))

cfg = AstrbotConfigEntry[SecureConfig].bind(
    group="api",
    name="secrets",
    default=SecureConfig(),
    description="API 密钥配置",
    cfg_dir=Path.cwd() / "config"
)

# 设置密钥(请勿！照猫画虎！请通过交互式/直接改文件的方式设置密钥，直接这样硬编码是不安全的！)
cfg.value.api_key.secret = "your-secret-key" # 会自动将密钥保存到不可篡改的地方（系统的密钥库内）
cfg.save() # 设置完记得保存

# 安全访问密钥
with cfg.value.api_key.ctx() as secret:
    print(f"Secret: {secret}")  # 仅在此上下文内可用

# 异步版本
async cfg.value.api_key.actx() as secret:
    ...


# 删除密钥

del cfg.value.api_key.secret


# 打印/记录到日志也无妨，防止误操作，只能通过with语句来获取secret

print(cfg.value.api_key) #安全
print(cfg.value.api_key.secret) #安全




```


## API 参考

### AstrbotConfigEntry

- `bind(group, name, default, description, cfg_dir)`: 绑定配置实例
- `save()`: 保存配置到文件
- `load()`: 从文件加载配置
- `value`: 访问配置对象

### AstrbotSecretKey

- `secret`: 属性设置/删除密钥（警告：直接访问返回 key_id）
- `ctx()`: 同步上下文管理器获取密钥
- `actx()`: 异步上下文管理器获取密钥

## 许可证

MIT License

