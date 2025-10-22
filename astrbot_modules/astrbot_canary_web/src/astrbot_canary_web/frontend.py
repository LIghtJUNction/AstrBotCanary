import zipfile
from contextlib import suppress
from logging import Logger, getLogger
from pathlib import Path

import requests
from tqdm import tqdm

logger: Logger = getLogger("astrbot.module.web.frontend")


class AstrbotCanaryFrontend:
    """直接使用Astrbot官方前端."""

    webroot: Path
    dashboard_release_url: str = (
        "https://github.com/AstrBotDevs/AstrBot/releases/{version}/download/dist.zip"
    )

    @classmethod
    def ensure(cls, webroot: Path) -> bool:
        """确保前端文件存在."""
        cls.webroot = webroot
        if cls.check(webroot):
            return True
        dist_zip_path: Path = cls.download(webroot)
        logger.info("Frontend files downloaded to %s", dist_zip_path)
        # extract downloaded zip into webroot/dist
        try:
            cls.extract_dist(dist_zip_path, webroot)
            dist_zip_path.unlink(missing_ok=True)
        except Exception:
            logger.exception("Failed to extract frontend zip")

        if cls.check(webroot):
            # 清除下载的zip文件

            with suppress(OSError, FileNotFoundError):
                dist_zip_path.unlink(missing_ok=True)
            return True
        # 第二次检查仍然失败
        return False

    @classmethod
    def check(cls, webroot: Path) -> bool:
        """检查前端文件夹文件结构是否正确."""
        index_file = webroot / "dist" / "index.html"
        return index_file.exists() and index_file.is_file()

    @classmethod
    def need_update(cls, webroot: Path) -> bool:
        """检查是否需要更新前端文件."""
        logger.info("正在检查是否需要更新,%s", webroot)
        return False

    @classmethod
    def download(cls, webroot: Path, version: str = "latest") -> Path:
        """同步下载前端文件到webroot--异步循环外
        返回:dist.zip文件路径.
        """
        cls.webroot = webroot
        _url: str = cls.dashboard_release_url.format(version=version)

        # prepare directories
        webroot.mkdir(parents=True, exist_ok=True)

        zip_path = webroot / "dist.zip"
        if zip_path.exists():
            return zip_path

        tmp_zip = webroot / (zip_path.name + ".tmp")

        # download to temporary zip file with requests (streamed)
        resp = requests.get(
            _url,
            headers={"User-Agent": "python-requests/2"},
            stream=True,
            timeout=30,
        )
        resp.raise_for_status()

        # try to get total size from headers
        total_size = None
        try:
            cl = resp.headers.get("Content-Length")
            if cl is not None:
                total_size = int(cl)
        except (ValueError, TypeError):
            total_size = None

        chunk_size = 16 * 1024
        with tmp_zip.open("wb") as out_f:
            # stream with progress
            if total_size is not None:
                with tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    desc=zip_path.name,
                ) as pbar:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if not chunk:
                            continue
                        out_f.write(chunk)
                        pbar.update(len(chunk))
            else:
                # unknown total size, use indeterminate progress
                with tqdm(unit="B", unit_scale=True, desc=zip_path.name) as pbar:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if not chunk:
                            continue
                        out_f.write(chunk)
                        pbar.update(len(chunk))

        # move temp zip into final path (atomic when possible)
        if tmp_zip.exists():
            tmp_zip.replace(zip_path)

        return zip_path

    @classmethod
    def extract_dist(cls, zip_path: Path, target_dir: Path) -> None:
        """Extract zip_path into target_dir.

        Simple behavior:
        - remove existing target_dir
        - extract archive into target_dir 注意:提取压缩包到指定目录包括压缩包文件名目录
        - 比如这里实际上是 target_dir / "dist"
        - if target_dir contains a single subdirectory, move its children up (flatten)
        """
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)
