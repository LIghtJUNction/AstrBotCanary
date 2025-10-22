import os

# 全角到半角符号映射表
full2half = {
    "，": ",",
    "。": ".",
    "！": "!",
    "？": "?",
    "【": "[",
    "】": "]",
    "（": "(",
    "）": ")",
    "《": "<",
    "》": ">",
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    "；": ";",
    "：": ":",
    "、": ",",
    "——": "-",
    "……": "...",
    "￥": "¥",
}


def convert_file(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        content = f.read()
    # 替换所有全角符号
    for zh, en in full2half.items():
        content = content.replace(zh, en)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def scan_and_convert(root: str) -> None:
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(".py"):
                convert_file(os.path.join(dirpath, filename))


if __name__ == "__main__":
    # 递归处理 src 和 astrbot_* 目录
    scan_and_convert("src")
    for d in os.listdir("."):
        if d.startswith("astrbot_") and os.path.isdir(d):
            scan_and_convert(d)
