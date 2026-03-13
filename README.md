# AstrBotCanary

注意：本项目为实验性分支，不是官方 AstrBot 版本。若需要稳定与兼容性更好的版本，请使用官方仓库：[Astrbot](https://github.com/AstrBotDevs/AstrBot)

实验性分支，面向未来设计

核心将由rust重构

核心主进程（rust编写）|  
                   | -- （可延迟加载的子进程）python插件运行时
                   | -- 插件dll/so库文件（设计中）
                   | -- 其他语言的运行时... 
                   
进程间采用UDS通信（unix），mmap高效存放“大数据”

