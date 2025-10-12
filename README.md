# AstrBotCanary

注意：本项目为实验性分支，不是官方 AstrBot 版本。若需要稳定与兼容性更好的版本，请使用官方仓库：https://github.com/AstrBotDevs/AstrBot

本项目旨在采用最新的 Python 特性与第三方库进行试验性开发，供社区探索新特性与实现方案之用。

---

## 目录
- [关于](#关于)
- [状态说明 / 兼容性](#状态说明--兼容性)
- [为何暂时不支持 Python 3.14](#为何暂时不支持-python-314)
- [开发进度](#开发进度)
- [开发计划 / 依赖选型](#开发计划--依赖选型)
- [文档](#文档)
- [系统支持](#系统支持)
- [快速使用（Windows）](#快速使用windows)
- [小贴士 (TIPS)](#小贴士-tips)
- [贡献与联系](#贡献与联系)
- [许可](#许可)

---

## 关于
AstrBotCanary 是 AstrBot 的一个实验性分支，面向追求最新语言特性和高性能 Web 运行时的开发者。通过引入像 Robyn、Rust 扩展等新技术，探索更高的性能和更简洁的实现路径。

本分支可能包含不稳定、API 变更或依赖还在适配阶段的实现，不建议在生产环境直接替换官方版本。

正在开发中... 以下内容为提前规划，暂时不要使用

# 安装
如果你需要安装在全局，直接uv tool install astrbot_canary即可

如果你希望不要安装在全局，你想安装在某个自定义文件夹内：
> uv venv .venv --python 3.13.8 （在当前目录新建虚拟环境）
新建一个.env文件：
并写入以下内容：
ASTRBOT_ROOT = "./.astrbot"
指定astrbot根目录为当前目录下的.astrbot文件夹
（如果没有，默认是~/.astrbot/）

然后：
> uv tool install astrbot_canary

如果你希望前端路径自定义？
你可以修改config/metadata.webroot.toml内的值
但是一般不建议自定义路径


---

## 状态说明 / 兼容性
- 项目性质：实验性（Canary）
- 当前进度：正在开发core模块
- 最低 Python 要求（当前）：Python 3.13.8+
- 目前仅提供 Windows 预编译包（包含扩展模块）；其他系统需要自行编译依赖。

---

## 为何暂时不支持 Python 3.14
本项目使用 Robyn（高性能 Web 框架），并且 Robyn 依赖通过 PyO3 编写的 Rust 扩展模块。当前 PyO3 对 Python 3.14 的支持尚不完善，因此本项目暂时以 3.13.8 作为兼容目标。一旦 PyO3 / Robyn 支持 Python 3.14，会在后续版本中尽快切换或发布兼容分支。

---

## 开发进度
- 正在实现：根模块，目标实现两个接口，一个对接插件加载器，一个对接显示模块（tui/web/...）

---

## 开发计划（依赖 / 选型示例）
- 消息分发+调度+定时：taskiq!
- Web 框架：Robyn（Rust + PyO3 驱动，高并发探索）
- TUI 框架：Textual
- 数据类型验证：pydantic，pydantic-settings
- 数据库 ：sqlite
ORM:sqlalchemy
- 插件系统设计：pluggy+入口点发现机制
- 接口设计：Protocols

- 动态验证一个模块是否符合协议

> 注：上面只是示例/候选库，具体选型以实现和兼容性为准。

---

## 文档
项目文档位于 `docs/`（仓库内）。  
在本项目语境下，区分：
- 模块（Module）：项目的核心功能组件
- 插件（Plugin）：由社区或第三方提供的扩展功能

请参考 `docs/` 获取更详细的开发与使用说明。

---

## 系统支持
- Windows：提供预编译版本（包含扩展模块）
- Linux / macOS：需要自行编译 Rust / PyO3 扩展与相关依赖

推荐使用 Python 3.13.8（或仓库指定的受支持版本）来获得最佳兼容性。

---

## 快速使用（Windows）
下面为最小化的上手提示，仅供参考：

1. 安装 Python（建议使用 3.13.8）  
   推荐使用 Microsoft Store 的 Python 管理器或 Windows 的包管理工具（详见下方小贴士）。
本项目已上传至pypi，后续通过pypi进行安装


2. 从pypi安装本项目
uv tool install aStrBoT.-_-_cAnarY
（等正式版出来我换成正常一点的，不过其实这样也能安装哈哈）
---

## 小贴士 (TIPS)
- 若使用 Windows，推荐使用 Microsoft 的 Python 安装管理器（应用商店或 `uv`/`py` 管理工具）来管理多个 Python 版本。示例：  
  - 安装 Microsoft Store 的 Python 管理器（BETA 版）：https://apps.microsoft.com/detail/9nq7512cxl7t?hl=zh-CN&gl=CN  
  - 使用该管理器安装：`py install 3.13.8`
  - 查看可用版本：`uv python list`
  - 同步项目版本（若使用 uv 管理）：`uv sync`

- Windows 以外平台需要自己编译 Rust / PyO3 扩展，建议安装 Rust toolchain（rustup）并按照扩展 README 中的构建说明操作。

---

# 开发指南
uv pip install -e .[all]


## 贡献与联系
欢迎贡献代码、Issue、PR 与讨论。  
请在提交前阅读仓库中的贡献指南（若有）与 `CODE_OF_CONDUCT`。

项目主页 / 参考： https://github.com/AstrBotDevs/AstrBot  
仓库维护者：LIghtJUNction

---

## 许可
本仓库遵循原项目所采用的许可证（请在仓库中查看 LICENSE 文件以确定具体许可条款）。
本项目采用与Astrbot相同的许可证:
GPLV3

---

