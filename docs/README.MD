# 规范文件夹

[spec](./spec)

# 名词约定

## 模块：Module

约定：模块一般指项目核心组件
只要实现了模块接口
允许任意替换
模块需要继承自`AstrbotBaseModule`抽象基类
模块总类有限，且应当从入口点加载
模块不一定需要在本项目中实现，本项目实现的模块作为默认回退
模块的入口点应该这样定义（加载器模块为例）：
[project.entry-points."astrbot.modules.loader"]
"canary_loader" = "astrbot_canary.loader.loader:AstrbotLoader"

如果新增模块：
"my_loader" = "my_pkg.loader.loader:my_Loader"
请你使用BASE模块提供的模块开发API 来实现模块

## 插件：Plugin

约定：插件一般指社区制作的功能扩展/附加组件
加载器模块将负责加载插件
AstrbotCanary支持热插拔插件，将兼容Astrbot插件
插件由加载器模块加载
加载器基于pluggy实现，支持新版插件，同时兼容Astrbot旧版插件
插件种类多且杂，请查看加载器模块定义的规范

## 根模块

根模块是项目的核心模块
作为项目启动的入口

## 规范注释（可选）

规范注释有助于他人阅读和理解代码
请在每个模块/插件的头部添加规范注释
规范注释格式参考[规范模板](./spec-template.md)

## 接口：Interface

模块只要实现了该接口
允许任意替换
接口应该定义在api中

## 笔记本 ：Notebook

笔记本是Jupyter Notebook的简称
笔记本文件后缀名为`.ipynb`
介绍：笔记本简单点说是支持运行代码的markdown文档，很适合写教程
笔记本还可以直接在浏览器中运行
本项目的教程/指南将使用笔记本编写

## 子解释器（因为项目不再是基于3.14，用不到）

子解释器是Python 3.14新增的功能：https://docs.python.org/zh-cn/3/library/concurrent.interpreters.html
简要介绍就是同一进程中的多个python解释器
解释器本身并不提供任何并发能力
对于插件，将采用子解释器隔离运行
官方文档给出的解释有一句：
多线程与多解释器结合使用时，可以实现真正的多核并行处理。

## 入口点

在pyproject.toml中定义的入口点
当你制作插件时
请声明入口点：astrbot.plugins
加载器模块自动加载这些入口点
入口点必须是一个类

## 解耦

解耦是指模块/插件之间不直接依赖
而是通过约定的接口/抽象基类/入口点进行交互
例如本项目，将插件与加载器解耦
插件不直接依赖加载器
而是动态调用加载器提供的API入口点
然而动态调用API入口点这些操作也不太方便

因此本项目提供一个独立的Helper库（后续的内容）
仅提供一些封装好的便捷函数，供模块-插件开发者使用
比如模块调试等有用功能
