import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple


def run_shell(shell, retry=True, retry_times=3):
    cmd = subprocess.Popen(
        shell,
        close_fds=True,
        shell=True,
        bufsize=1,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )

    if retry and cmd.returncode != 0:
        time.sleep(1)
        if retry_times > 0:
            return run_shell(shell, retry=True, retry_times=retry_times - 1)
        print('\nShell出现异常，请自行查看课程文件是否转码成功')
    return cmd.returncode


def ts2mp4(file):
    file = Path(file)
    ffmpeg = Path('ffmpeg.exe')
    basename = file.name.split('.ts')[0]
    file_dir = file.parent
    output = file_dir.joinpath(basename)
    # cmd = str(ffmpeg) + ' -i "' + str(file) + '" -c copy "' + str(output) + '".mp4'
    cmd = f'{ffmpeg} -i "{file}" -c copy "{output}.mp4"'
    # 这个命令会报错，但是我不熟悉ffmpeg，而且似乎输出视频没有毛病，所以屏蔽了错误输出
    run_shell(cmd, retry_times=False)
    file.unlink()


def clear_screen():
    if sys.platform.startswith('win'):
        os.system('cls')
    else:
        os.system('clear')


def parse_page(text: str) -> Tuple[int]:
    """
    解析页码,重复页码会被省略
    格式
     页码 或 页码范围(起始页码-结束页码)
     多个可用,进行分割
    @param text: 页码文本
    @return: 页码列表
    """
    splits = text.replace("，", ",").split(",")
    pages = []

    for page in splits:
        # 范围页码
        if page:
            if '-' in page:
                s, e = page.split('-')
                pages.extend(range(int(s), int(e) + 1))
            else:
                pages.append(int(page))

    return tuple(set(pages))


def size_format(size: int, *, pro: int = 1.0, dec: int = 2):
    """文件大小格式化
    :param size: 文件大小，单位byte
    :param pro: 单位转换进行的比例
    :param dec: 文件大小浮点数的精确单位
    :return: 文件单位格式化大小
    """
    unit: list = ["B", "KB", "MB", "GB", "TB", "PB"]
    pos: int = 0
    while size >= 1024 * pro:
        size /= 1024
        pos += 1
        if pos >= len(unit):
            break
    return str(round(size, dec)) + unit[pos]
