# AstrBotCanary

[![codecov](https://codecov.io/gh/LIghtJUNction/AstrBotCanary/branch/main/graph/badge.svg)](https://codecov.io/gh/LIghtJUNction/AstrBotCanary)

注意：本项目为实验性分支，不是官方 AstrBot 版本。若需要稳定与兼容性更好的版本，请使用官方仓库：https://github.com/AstrBotDevs/AstrBot
本项目旨在采用最新的 Python 特性与第三方库进行试验性开发，供社区探索新特性与实现方案之用。

______________________________________________________________________

## 代码风格

本项目偏激进，代码风格由ruff的规则约束
但存在两条意外：
第一，不开启D类检查
此为文档检查，当项目稳定后（时间不确定），会统一规范各类注释。

第二，暂不开启N类检查，此为变量命名检查，当前命名风格并未完全按照PEP8进行，而是依据使用频率，美观程度综合决定。

整体风格设计上：

- 多数类名使用Astrbot开头，驼峰式命名

- 私有变量，内部函数，下划线开头

- 公共函数，一般采用蛇形
部分采用小驼峰（getLogger）

比如~~findEntry~~（后来我嫌两个类管配置没有什么必要，精简了）

- 生命周期函数，C#风格（具体来说就是Unity的Monobehaviey类的三个生命周期）

Awake: 初始化

Start: 启动

OnDestroy: 终止

后续可能会拓展更多方法.

## 项目结构

基于uv的现代化布局，mono repo布局
，src包含核心模块以及根模块

- astrbot_modules：子项目文件夹
均直接依赖于astrbot_api，解耦于astrbot_core

- astrbot_plugins：官方提供支持的插件目录，插件依赖于astrbot_api（~~原设计依赖于加载器api，后因设计复杂度放弃~~）

## 目录

- [关于](#%E5%85%B3%E4%BA%8E)
- [状态说明 / 兼容性](#%E7%8A%B6%E6%80%81%E8%AF%B4%E6%98%8E--%E5%85%BC%E5%AE%B9%E6%80%A7)
- [覆盖率测试](#%E8%A6%86%E7%9B%96%E7%8E%87%E6%B5%8B%E8%AF%95)
- [为何暂时不支持 Python 3.14](#%E4%B8%BA%E4%BD%95%E6%9A%82%E6%97%B6%E4%B8%8D%E6%94%AF%E6%8C%81-python-314)
- [开发进度](#%E5%BC%80%E5%8F%91%E8%BF%9B%E5%BA%A6)
- [开发计划 / 依赖选型](#%E5%BC%80%E5%8F%91%E8%AE%A1%E5%88%92--%E4%BE%9D%E8%B5%96%E9%80%89%E5%9E%8B)
- [文档](#%E6%96%87%E6%A1%A3)
- [系统支持](#%E7%B3%BB%E7%BB%9F%E6%94%AF%E6%8C%81)
- [快速使用（Windows）](#%E5%BF%AB%E9%80%9F%E4%BD%BF%E7%94%A8windows)
- [小贴士 (TIPS)](#%E5%B0%8F%E8%B4%B4%E5%A3%AB-tips)
- [贡献与联系](#%E8%B4%A1%E7%8C%AE%E4%B8%8E%E8%81%94%E7%B3%BB)
- [许可](#%E8%AE%B8%E5%8F%AF)

______________________________________________________________________

## 关于

AstrBotCanary 是 AstrBot 的一个实验性分支。
通过引入像 Rust 扩展等新技术，探索更高的性能和更简洁的实现路径。

本分支可能包含不稳定、API 变更或依赖还在适配阶段的实现，不建议在生产环境直接替换官方版本。

正在开发中... 以下内容为提前规划，暂时不要使用

# 安装（开发版本暂未上传至pypi）

如果你需要安装在全局，直接uv tool install astrbot_canary即可

如果你希望不要安装在全局，你想安装在某个自定义文件夹内：

> uv venv .venv --python 3.13.8 （在当前目录新建虚拟环境）
> 新建一个.env文件：
> 并写入以下内容：
> ASTRBOT_ROOT = "./.astrbot"
> 指定astrbot根目录为当前目录下的.astrbot文件夹
> （如果没有，默认是~/.astrbot/）

然后：

> uv tool install astrbot_canary

如果你希望前端路径自定义？
配置文件夹：config/
但是一般不建议自定义路径

______________________________________________________________________

## 状态说明 / 兼容性

- 项目性质：实验性（Canary）
- 当前进度：正在开发core模块
- 最低 Python 要求（当前）：Python 3.13.8+
- 目前仅提供 Windows 预编译包（包含扩展模块）；其他系统需要自行编译依赖。

______________________________________________________________________

## 为何暂时不支持 Python 3.14

当前 PyO3 对 Python 3.14 的支持尚不完善，因此本项目暂时以 3.13.8 作为兼容目标。

______________________________________________________________________

## 开发进度

- 正在实现：任务调度系统

## 任务系统

- astrbot将注册一系列全局任务
- 模块/插件可以注册局部任务，局部任务将覆盖全局任务达到重写效果
- 任务支持 任务前后钩子，使得灵活性进一步提高
- 我的笔记在example/astrbot_tasks.ipynb

______________________________________________________________________

## 开发计划（依赖 / 选型示例）

- 消息分发+调度+定时：taskiq! +0ORJSONSerializer+FastStream（未使用）

- Web 框架：Fastapi(robyn有无法接受的bug）

- TUI 框架：Textual

- 数据类型验证：pydantic，pydantic-settings

- 数据库 ：sqlite
  ORM:sqlalchemy

- 插件系统设计：pluggy+入口点发现机制

- 接口设计：Protocols
  备选：
  pyahocorasick（文本处理）

- 动态验证一个模块是否符合协议

> 注：上面只是示例/候选库，具体选型以实现和兼容性为准。

______________________________________________________________________

## 覆盖率测试

- uv tool install coverage

- coverage run -m pytest

- 或者使用以下命令

- pytest --cov=src --cov-report=term-missing

- 输出为xml/json/html

- pytest --cov=src --cov-report=xml

- coverage xml/json/html

查看覆盖率：

- 点击最顶上的徽标即可

## 文档

项目文档位于 `docs/`（仓库内）。
在本项目语境下，区分：

- 模块（Module）：项目的核心功能组件
- 插件（Plugin）：由社区或第三方提供的扩展功能

请参考 `docs/` 获取更详细的开发与使用说明。

______________________________________________________________________

## 系统支持

- Windows：提供预编译版本（包含扩展模块）
- Linux / macOS：需要自行编译 Rust / PyO3 扩展与相关依赖

推荐使用 Python 3.13.8（或仓库指定的受支持版本）来获得最佳兼容性。

______________________________________________________________________

## 快速使用（Windows）

下面为最小化的上手提示，仅供参考：

1. 安装 Python（建议使用 3.13.8）
   推荐使用 Microsoft Store 的 Python 管理器或 Windows 的包管理工具（详见下方小贴士）。
   本项目已上传至pypi，后续通过pypi进行安装

1. 从pypi安装本项目
   uv tool install aStrBoT.-\_-\_cAnarY
   （稳定版发布后再改）

______________________________________________________________________

## 小贴士 (TIPS)

- 若使用 Windows，推荐使用 Microsoft 的 Python 安装管理器（应用商店或 `uv`/`py` 管理工具）来管理多个 Python 版本。示例：

  - 安装 Microsoft Store 的 Python 管理器（BETA 版）：https://apps.microsoft.com/detail/9nq7512cxl7t?hl=zh-CN&gl=CN
  - 使用该管理器安装：`py install 3.13.8`
  - 查看可用版本：`uv python list`
  - 同步项目版本（若使用 uv 管理）：`uv sync`

- Windows 以外平台需要自己编译 Rust / PyO3 扩展，建议安装 Rust toolchain（rustup）并按照扩展 README 中的构建说明操作。

______________________________________________________________________

# 开发指南

- uv sync --dev
- 请使用pre-commit
- pre-commit install

- 本项目在开发时使用了几乎最严格的类型检查，尽量减少运行时的错误

- 命名风格大多数符合python规范，小部分（比如Awake，OnDestroy等生命周期函数则是c#风格）


## 贡献与联系

欢迎贡献代码、Issue、PR 与讨论。
请在提交前阅读仓库中的贡献指南（若有）与 `CODE_OF_CONDUCT`。

项目主页 / 参考： https://github.com/AstrBotDevs/AstrBot

Canary仓库维护者：LIghtJUNction

______________________________________________________________________

## 许可

本仓库遵循原项目所采用的许可证（请在仓库中查看 LICENSE 文件以确定具体许可条款）。
本项目采用与Astrbot相同的许可证:
GPLV3

______________________________________________________________________
