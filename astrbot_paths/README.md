# Astrbot Paths

- 规范化路径获取



- 默认值为：

- ~/.astrbot/

- 如果介意设置到C盘（主目录），可以按以下方法指定根目录：

- 请在当前目录下新建.env文件自定义根目录

- 或者通过环境变量指定

'''env

# astrbot根目录
ASTRBOT_ROOT = "./.astrbot"

'''

# 使用方法速览
'''python
paths = AstrbotPaths.getPaths("pypi_name") # pypi_name将会被规范化处理

print(paths.data) #模块数据目录

print(paths.config) #模块配置目录

print(paths.root) #模块自身的根

全部基于pathlib Path类

可使用以下语法糖：

paths.data / "xxx.db"


'''