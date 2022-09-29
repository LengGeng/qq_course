from pathlib import Path

import requests
import datetime
from Crypto.Cipher import AES
import httpx

from logger import logger
from utils import ts2mp4


def add_to_16(value):
    while len(value) % 16 != 0:
        value += '\0'
    return str.encode(value)


def decrypt(ciphertext, key):
    iv = ciphertext[:AES.block_size]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = cipher.decrypt(ciphertext[AES.block_size:])
    return plaintext.rstrip(b'\0')


def decrypt_file(filename, key):
    with open(filename, 'rb') as f:
        ciphertext = f.read()
    dec = decrypt(ciphertext, key)
    with open(filename, 'wb') as f:
        f.write(dec)


def get_key(filename):
    with open(filename, 'rb') as f:
        key = f.read()
    return key


def download(file_url, file):
    res = requests.get(file_url)
    with open(file, 'wb') as f:
        f.write(res.content)
    return 0


def progress(percent, width=30, filename=None):
    left = int(width * percent // 100)
    right = width - left
    print(
        filename,
        '\r[',
        '■' * left,
        ' ' * right,
        ']',
        f' {percent:.0f}%',
        sep='',
        end='',
        flush=True,
    )


def lg_download(file_url, filename, path, headers=None):
    # 用来下载大文件，有进度条
    file = str(Path(path, filename))
    response = requests.get(file_url, stream=True, headers=headers)
    size = 0
    chunk_size = 1024
    content_size = int(response.headers['content-length'])
    if response.status_code == 200:
        print(
            '正在下载 {filename},大小: {size:.2f} MB'.format(
                filename=filename, size=content_size / chunk_size / 1024
            )
        )

        with open(file, 'wb') as f:
            last_show_time = datetime.datetime.now()
            delta_time = datetime.timedelta(seconds=1)
            for data in response.iter_content(chunk_size=chunk_size):
                f.write(data)
                size += len(data)
                if datetime.datetime.now() - last_show_time > delta_time:
                    progress(size / content_size * 100, filename=filename)
                    last_show_time = datetime.datetime.now()


async def async_download(url, path: Path, filename):
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(10, connect=5, read=5, write=5, pool=5)
    )
    base_file = path.joinpath(filename)
    size = 0
    async with client.stream('GET', url) as response:
        content_size = int(response.headers['content-length'])
        if base_file.exists():
            if base_file.stat().st_size == content_size:
                return

        with open(base_file, 'wb') as f:
            current_size = 0
            last_show_time = datetime.datetime.now()
            delta_time = datetime.timedelta(seconds=1)
            async for chunk in response.aiter_bytes(chunk_size=1024):
                f.write(chunk)
                size += len(chunk)
                if size > current_size:
                    current_size = max(size, current_size)
                if datetime.datetime.now() - last_show_time > delta_time:
                    progress(size / content_size * 100, filename=filename)
                    last_show_time = datetime.datetime.now()
    logger.info('Download ' + filename)
    await client.aclose()


def _download(url, path: Path, filename):
    client = httpx.Client(timeout=httpx.Timeout(10, connect=5, read=5, write=5, pool=5))
    filename_ext = filename + '.ts'
    base_file = path.joinpath(filename_ext)
    size = 0
    with client.stream('GET', url) as response:
        content_size = int(response.headers['content-length'])
        if base_file.exists() and base_file.stat().st_size == content_size:
            return
        with open(base_file, 'wb') as f:
            current_size = 0
            last_show_time = datetime.datetime.now()
            delta_time = datetime.timedelta(seconds=1)
            for chunk in response.iter_bytes():
                f.write(chunk)
                size += len(chunk)
                current_size = size
                if datetime.datetime.now() - last_show_time > delta_time:
                    progress(current_size / content_size * 100, filename=filename)
                    last_show_time = datetime.datetime.now()


async def download_single(ts_url, key_url, filename, path):
    print(f"{filename} 开始下载！")
    # 处理路径
    filename = filename.replace('/', '／').replace('\\', '＼')
    ts_file: Path = path.joinpath(f"{filename}.ts")
    key_file = path.joinpath("key")
    video_file = path.joinpath(f"{ts_file.stem}.mp4")
    # 判断是否下载过
    if video_file.exists():
        print(f"{video_file} 已存在！")
        return
    # 下载视频
    await async_download(ts_url, path, ts_file.name)
    # _download(ts_url, path, filename)
    # 下载秘钥
    download(file_url=key_url, file=key_file)
    # 解密文件
    key = get_key(key_file)
    decrypt_file(ts_file, key)
    key_file.unlink()
    # 合成 MP4
    ts2mp4(ts_file)
    print(f"\n{filename} 下载完成！")
