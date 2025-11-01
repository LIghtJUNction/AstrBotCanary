# Project Context

## Purpose
AstrBotCanary 是一个模块化的 Python 机器人框架，提供插件系统、配置管理、路径管理和任务队列功能。项目采用依赖注入（Dishka）和插件架构（Pluggy），支持动态加载核心模块、加载器、Web UI 和 TUI 模块。

## Tech Stack
- **Language**: Python 3.11+ (使用 `from __future__ import annotations`)
- **Package Manager**: uv (用于构建和依赖管理)
- **Framework**: 
  - Pluggy (模块/插件管理)
  - Dishka (依赖注入)
  - Taskiq (异步任务队列)
  - Pydantic (数据验证和配置)
  - FastAPI (Web API, 在 canary_web 模块中)
- **Testing**: pytest (推断)
- **Type Checking**: Mypy, Pyright/Pylance
- **Linter**: Ruff

## Project Conventions

### Code Style
- **格式化**: Ruff 自动格式化
- **命名约定**:
  - 类名: `PascalCase` (如 `AstrbotRootModule`, `IAstrbotPaths`)
  - 函数/方法: `snake_case` (如 `get_paths`, `bind`)
  - 生命周期方法: `PascalCase` (如 `Awake()`, `Start()`, `OnDestroy()`)
  - 常量: `UPPER_SNAKE_CASE` (如 `ASTRBOT_MODULES_HOOK_NAME`)
  - 类型变量: 大写单字母 (如 `T`)
- **导入顺序**: 标准库 → 第三方库 → 本地模块 → TYPE_CHECKING 块
- **类型注解**: 强制使用类型提示，使用 `TYPE_CHECKING` 避免循环导入
- **文档字符串**: 中文文档，使用三引号，简洁描述用途

### Architecture Patterns
- **模块化架构**: 核心功能拆分为独立的 Python 包（`astrbot_modules/`）
- **接口抽象**: 使用 ABC 定义接口（`IAstrbotModule`, `IAstrbotConfigEntry`, `IAstrbotPaths`）
- **依赖注入**: Dishka Provider 提供核心服务（broker, log_handler, paths, config_entry）
- **插件系统**: Pluggy hookspecs 和 hookimpls 实现模块生命周期管理
- **配置管理**: 
  - Pydantic BaseModel 用于配置数据模型
  - TOML 文件存储配置
  - `bind()` 工厂方法用于配置绑定
- **路径管理**: 统一的路径管理器（root, home, config, data, log）
- **任务队列**: Taskiq 支持多种 broker（InMemory, Redis, RabbitMQ, NATS 等）

### Testing Strategy
- 单元测试位于 `test/` 目录
- 使用 pytest 作为测试框架
- 测试文件命名: `test_*.py`
- 优先使用工具运行测试而非终端命令

### Git Workflow
- **主分支**: `main`
- **提交约定**: 未明确定义，建议使用语义化提交
- **构建命令**: `uv build --all`
- **Linting**: `ruff check --fix`

## Domain Context
- **模块类型**: CORE, LOADER, WEB, TUI (定义在 `AstrbotModuleType` 枚举)
- **生命周期**: 
  - `Awake()` - 模块初始化
  - `Start()` - 模块启动
  - `OnDestroy()` - 模块清理
- **Entry Points**: 使用 `astrbot.modules` entry point group 发现和加载模块
- **Provider Registry**: 全局注册表用于跨模块访问 Dishka 容器和 providers
- **日志系统**: 异步日志处理器，可配置捕获范围（astrbot, module, plugin）

## Important Constraints
- Python 版本: 3.11+ (使用现代类型注解语法)
- Windows 兼容性: 主要开发环境为 Windows (PowerShell)
- 类型安全: 严格的类型检查（Mypy, Pylance）
- 向后兼容: 接口变更需要通过 OpenSpec 提案
- 配置持久化: 配置必须可序列化为 TOML

## External Dependencies
- **Pydantic**: 数据验证和配置模型
- **Pluggy**: 插件管理系统
- **Dishka**: 依赖注入容器
- **Taskiq**: 异步任务队列（支持多种 broker/backend）
- **Rich**: 终端美化和日志输出
- **Click**: CLI 交互（模块选择）
- **FastAPI**: Web 框架（canary_web 模块）
