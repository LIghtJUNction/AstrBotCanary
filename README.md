# AstrBotCanary

[![codecov](https://codecov.io/gh/LIghtJUNction/AstrBotCanary/branch/main/graph/badge.svg)](https://codecov.io/gh/LIghtJUNction/AstrBotCanary)

注意：本项目为实验性分支，不是官方 AstrBot 版本。若需要稳定与兼容性更好的版本，请使用官方仓库：[Astrbot](https://github.com/AstrBotDevs/AstrBot)

## Astrbot paths


```python
# 将从环境变量/.env文件读取Astrbot根目录（数据目录/data目录） 
from astrbot_paths import AstrbotPaths
paths = AstrbotPaths.getPaths("plugin_a") # 初始化
print(paths.config) # 输出 plugin_a 配置文件路径
```

...

## Astrbot Config



```python
from pathlib import Path
from random import randint
from pydantic import BaseModel
from astrbot_config import AstrbotConfigEntry

class SubConfigExample(BaseModel):
detail: str
enabled: bool

class ConfigExample(BaseModel):
name: str
value: int
sub_config: SubConfigExample

cfg = AstrbotConfigEntry[ConfigExample].bind(
group = "A",
name = "example_config",
default = ConfigExample(
name="default_name",
value=42,
sub_config=SubConfigExample(
detail="default_detail",
enabled=True
)
),
description = "An example configuration entry for demonstration purposes.",
cfg_dir = Path.cwd() / "config_examples"
)

print(cfg.value)  # Access the current configuration value

cfg.value.name = "new_name" + str(randint(1, 100))  # Modify the configuration

cfg.save()  # Save the updated configuration back to file

print(cfg.value)  # Verify the saved configuration


```



## Astrbot messages


...
