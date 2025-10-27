
# 基于taskiq-dependencies 的定制版
- 修改如下：
- 针对3.13+进行修改
- 依据：https://docs.python.org/3/howto/annotations.html#annotations-howto
- 不使用get_type_hint函数获取type_hint
- 新增wrapt库

# 许可证：MIT License
=======
# AstrbotInjector

AstrbotInjector 是基于wrapt库的极简依赖注入库

属于Astrbot Canary的子项目


## 安装

```bash
pip install astrbot-injector

uv pip install astrbot-injector

# 添加到项目

uv add astrbot-injector

```

## 使用方法

### 1. 全局依赖注入

全局依赖可以在整个应用中共享。首先，使用 `AstrbotInjector.set()` 设置全局依赖，然后用 `@AstrbotInjector.inject` 装饰器自动注入。

```python
from astrbot_injector import AstrbotInjector

# 设置全局依赖
AstrbotInjector.set("database", "MySQL Connection")
AstrbotInjector.set("config", {"host": "localhost", "port": 3306})

# 定义一个需要注入依赖的函数
@AstrbotInjector.inject
def connect_to_db(database: str, config: dict) -> str:
    return f"Connected to {database} at {config['host']}:{config['port']}"

# 调用函数，依赖会自动注入
result = connect_to_db()
print(result)  # 输出: Connected to MySQL Connection at localhost:3306
```

如果手动提供参数，注入器不会覆盖它们：

```python
result = connect_to_db(database="PostgreSQL")
print(result)  # 输出: Connected to PostgreSQL at localhost:3306
```

### 2. 局部依赖注入

局部依赖只在特定的注入器实例中有效，适合模块级别的依赖管理。

```python
# 创建局部注入器
local_injector = AstrbotInjector("my_module")
local_injector.set("logger", "FileLogger")
local_injector.set("cache", "RedisCache")

# 使用局部注入器装饰函数
@local_injector.inject
def process_data(logger: str, cache: str, data: str = "default") -> str:
    return f"Processing {data} with {logger} and {cache}"

# 调用函数
result = process_data()
print(result)  # 输出: Processing default with FileLogger and RedisCache
```

### 3. 类属性注入

依赖注入器也可以为类属性注入值。

```python
# 设置全局依赖
AstrbotInjector.set("service", "UserService")

# 装饰类
@AstrbotInjector.inject
class MyController:
    service: str | None = None
    version: str = "1.0"

# 检查类属性
print(f"Service: {MyController.service}")  # 输出: Service: UserService
print(f"Version: {MyController.version}")  # 输出: Version: 1.0
```

### 4. 方法注入

支持类方法和静态方法的注入。

```python
# 设置依赖
AstrbotInjector.set("validator", "EmailValidator")

class UserManager:
    @classmethod
    @AstrbotInjector.inject
    def validate_user(cls, validator: str, email: str) -> str:
        return f"Validating {email} with {validator}"

    @staticmethod
    @AstrbotInjector.inject
    def send_notification(validator: str, message: str) -> str:
        return f"Sending notification: {message} via {validator}"

# 调用方法
print(UserManager.validate_user(email="user@example.com"))  # 输出: Validating user@example.com with EmailValidator
print(UserManager.send_notification(message="Welcome!"))  # 输出: Sending notification: Welcome! via EmailValidator
```

### 5. 使用 Dep 指定依赖键

可以使用 `Dep` 类在默认值中指定依赖键，允许自定义依赖名称。

```python
from astrbot_injector import AstrbotInjector, Dep

# 设置依赖
AstrbotInjector.set("db", "MySQL")
AstrbotInjector.set("logger", "ConsoleLogger")

# 使用 Dep 在函数参数默认值中指定键
@AstrbotInjector.inject
def connect(db: str = Dep("db"), log: str = Dep("logger")) -> str:
    return f"Connected to {db} with {log}"

# 调用
print(connect())  # 输出: Connected to MySQL with ConsoleLogger

# 对于类
@AstrbotInjector.inject
class MyService:
    database: str = Dep("db")
    logger: str = Dep("logger")

print(f"DB: {MyService.database}, Log: {MyService.logger}")
```

#### 动态依赖和缓存

`Dep` 还支持动态依赖解析和可选缓存，适用于需要运行时计算的依赖。

```python
import time
from astrbot_injector import AstrbotInjector, Dep

# 静态依赖
AstrbotInjector.set("package_name", "astrbot_injector")

# 动态依赖：每次调用时计算当前时间
@AstrbotInjector.inject
def get_info(package_name: str = Dep("package_name"), timestamp: float = Dep(lambda: time.time())) -> str:
    return f"Package {package_name} at {timestamp}"

print(get_info())  # 输出类似: Package astrbot_injector at 1700000000.0

# 带缓存的动态依赖：只计算一次
@AstrbotInjector.inject
def get_cached_info(package_name: str = Dep("package_name"), cached_time: float = Dep(lambda: time.time(), cache=True)) -> str:
    return f"Cached time for {package_name}: {cached_time}"

print(get_cached_info())  # 第一次计算并缓存
time.sleep(1)
print(get_cached_info())  # 使用缓存值，时间不变
```

对于类属性，也支持动态依赖：

```python
@AstrbotInjector.inject
class DynamicService:
    name: str = Dep("package_name")
    metadata: dict = Dep(lambda: {"version": "1.0", "author": "LIghtJUNction"}, cache=True)
```

### 6. 错误处理

如果依赖不存在且未提供参数，会抛出 `TypeError`。

```python
@AstrbotInjector.inject
def risky_function(missing_dep: str) -> str:
    return f"Got {missing_dep}"

# 这会抛出 TypeError
try:
    risky_function()
except TypeError as e:
    print(f"Error: {e}")  # 输出: Error: risky_function() missing 1 required positional argument: 'missing_dep'
```

## 总结

`AstrbotInjector` 提供了一种简单的方式来管理依赖注入，支持全局和局部作用域，以及函数、方法和类属性的注入，还可以通过 Dep 类自定义依赖键或动态解析依赖，并支持缓存以优化性能。它有助于减少代码中的硬编码依赖，提高代码的可测试性和可维护性。

更多高级用法可以参考测试文件或源码。
>>>>>>> Stashed changes
