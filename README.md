# AstrBotCanary
This is not an officially supported Astrbot
[Astrbot](https://github.com/AstrBotDevs/AstrBot)
注意：本项目为实验性项目，作为实验性版本
本项目将采用能采用的最新python版本，使用最新的特性和库
如要稳定，兼容，请使用官方版本
目前无法使用3.14的原因如下：
依赖于Robyn(一个高性能的Web框架)
Robyn是使用pyo3制作的rust扩展模块
而pyo3（用于制作Python的rust扩展模块）暂不支持3.14

# 开发进度
- 目前正在实现WEB模块


# DOCS
[docs](./docs)
在本项目语境下，模块和插件是不同的概念
模块是项目的核心组成部分
插件是社区制作的功能扩展/附加组件

# 支持情况
- 仅支持Windows预编译版本（包含拓展模块）
- 其他系统需自行编译

- 需要Python 3.13.8+


# TIPS

卸载python luncher
下载[BETA版本的python 安装管理器](https://apps.microsoft.com/detail/9nq7512cxl7t?hl=zh-CN&gl=CN)
py install 3.13.8 ( uv 可下载的版本不齐全 )

uv python list 查看可用版本

uv sync 同步本项目
