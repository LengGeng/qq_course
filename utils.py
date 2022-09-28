import json
import os
import subprocess
import sys
import time
from pathlib import Path

from requests.cookies import cookiejar_from_dict


def print_menu(menu):
    for item in menu:
        print(str(menu.index(item)) + '. ' + item)


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
    cmd = str(ffmpeg) + ' -i "' + str(file) + '" -c copy "' + str(output) + '".mp4'
    # 这个命令会报错，但是我不熟悉ffmpeg，而且似乎输出视频没有毛病，所以屏蔽了错误输出
    run_shell(cmd, retry_times=False)
    file.unlink()


def load_json_cookies():
    cookies = Path('cookies.json')
    if cookies.exists():
        return cookiejar_from_dict(json.loads(cookies.read_bytes()))


def clear_screen():
    if sys.platform.startswith('win'):
        os.system('cls')
    else:
        os.system('clear')
