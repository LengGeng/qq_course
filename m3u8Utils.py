import re
from pathlib import Path
from subprocess import Popen, DEVNULL
from urllib.parse import urljoin

import requests
from Crypto.Cipher import AES


def get_m3u8_content(url):
    """
    获取 m3u8 文件内容
    @param url: m3u8 文件链接
    @return: m3u8 文件内容
    """
    with requests.get(url, timeout=10) as response:
        return response.text


def parse_m3u8(url: str, content: str = None, join_ts_url: bool = True):
    """
    解析 m3u8 文件中的 key_url,ts_urls
    @param url: m3u8 文件链接,拼接 ts_url 等操作会用到
    @param content: m3u8 文件内容,存在内容时不会再请求链接
    @param join_ts_url: 拼接 ts_url 完整路径
    @return: key_url,ts_urls
    """
    if content is None:
        content = get_m3u8_content(url)

    # 判断是否是 m3u8 文件
    if "#EXTM3U" not in content:
        raise Exception("非 m3u8 的链接")

    # 判断是否还有其他 m3u8 链接
    if "EXT-X-STREAM-INF" in content:
        file_line = content.splitlines()
        for line in file_line:
            if '.m3u8' in line:
                url = urljoin(url, line)
                content = get_m3u8_content(url)

    # 解析 key_url
    method, key_url = re.compile('#EXT-X-KEY:METHOD=(.*?),URI="(.*?)"').findall(content)[0]
    # 解析 ts_urls
    ts_urls = re.compile(".*\\.ts\\?.*").findall(content)
    # 拼接 ts_url 完整路径
    if join_ts_url:
        ts_urls = [urljoin(url, ts_url) for ts_url in ts_urls]
    return key_url, ts_urls


def download_ts_split(ts_urls, key, output_dir: Path, progress_bar):
    """
    下载 m3u8 ts 文件列表
    @param ts_urls: ts 文件列表
    @param key: 解密文件,没有不进行解密
    @param output_dir: 保存目录
    @return: 下载的 ts 路径列表
    @param progress_bar: 下载进度条
    """
    output_files = []

    if key:
        # 解密器
        decryptor = AES.new(key, AES.MODE_CBC, key)

    for i, ts_url in enumerate(ts_urls):
        res = requests.get(ts_url)
        progress_bar.addition(len(res.content))
        output_path = output_dir.joinpath(f"{i}.ts")
        output_files.append(output_path.resolve())

        # # AES 解密
        if key:
            output_path.write_bytes(decryptor.decrypt(res.content))
        else:
            output_path.write_bytes(res.content)

    return output_files


def download_m3u8(m3u8_url, output_path: Path, handle_key_url=None, handle_ts_url=None, headers: str = None):
    """
    下载 m3u8
    @param m3u8_url: m3u8 文件链接
    @param output_path: 输出文件路径
    @param handle_key_url: 处理 key_url 的函数 handle_key_url(key_url)->new_key_url key_url:解析到的 key_url
    @param handle_ts_url: 处理 ts_url 的函数 handle_ts_url(i,ts_url)->new_ts_url i:ts_url 的索引,ts_url: 解析到的 ts_url
    @param headers: 请求的 headers,使用 ; 分隔每一项 header
    @return:
    """
    content = get_m3u8_content(m3u8_url)
    key_url, ts_urls = parse_m3u8(m3u8_url, content, join_ts_url=False)

    # 处理 key_url
    if handle_key_url and callable(handle_key_url):
        new_key_url = handle_key_url(key_url)
        content = content.replace(key_url, new_key_url)

    # 处理 ts_urls
    if handle_ts_url and callable(handle_ts_url):
        for i, ts_url in enumerate(ts_urls):
            new_ts_url = handle_ts_url(i, ts_url)
            content = content.replace(ts_url, new_ts_url)

    m3u8_file = output_path.parent.joinpath("video.m3u8")
    m3u8_file.write_text(content)

    # 下载 m3u8
    cmd = f'ffmpeg -allowed_extensions ALL -protocol_whitelist "file,http,https,tls,tcp,crypto"'
    cmd += f' -i "{m3u8_file}" -c copy "{output_path}"'

    if headers:
        cmd += f' -headers "{headers}"'
    Popen(cmd, shell=True, stdout=DEVNULL, stderr=DEVNULL).wait()
    # 删除 m3u8 文件
    m3u8_file.unlink()


def merge_ts_ffmpeg(ts_files, output_path: Path):
    """
    拼接 ts 文件
    通过 ffmpeg 直接拼接所有 ts 文件
    @param ts_files: ts 文件路径列表
    @param output_path: 输出文件路径
    @return:
    """
    output_dir = output_path.parent
    ts_files_txt = output_dir.joinpath("ts_files.txt")
    # 生成 ts_files.txt
    with ts_files_txt.open('w') as fp:
        for ts_file in ts_files:
            fp.write(f"file '{ts_file}'\n")

    cmd = f'ffmpeg -f concat -safe 0 -i "{ts_files_txt}" -c copy "{output_path}"'
    p = Popen(cmd, shell=True, stdout=DEVNULL, stderr=DEVNULL)
    return_code = p.wait()
    if return_code:
        print(f"{return_code} 合并 ts 文件发生异常")
    else:
        print(f"合并 ts 文件完成")
    # 删除 ts 文件
    del_ts_cmd = f'del /Q "{output_dir.joinpath("*.ts")}"'
    Popen(del_ts_cmd, shell=True, stdout=DEVNULL, stderr=DEVNULL).wait()


def merge_ts_copy(ts_dir: Path, output_path: Path):
    """
    拼接 ts 文件
    通过 copy 命令建目录下所有的 ts 文件合并到一起再使用 ffmpeg 进行调整
    @param ts_dir: ts 文件所在目录,会合并目录下所有的 ts 文件
    @param output_path: 输出文件路径
    @return:
    """
    ts_files = ts_dir.joinpath("*.ts")
    tmp_file = ts_dir.joinpath("tmp.mp4")
    # copy 所有 ts 文件
    copy_ts_cmd = f'copy /b "{ts_files}" "{tmp_file}"'
    Popen(copy_ts_cmd, shell=True, stdout=DEVNULL, stderr=DEVNULL).wait()
    # 处理临时将文件
    cmd = f'ffmpeg -i "{tmp_file}" -c copy "{output_path}"'
    Popen(cmd, shell=True, stdout=DEVNULL, stderr=DEVNULL).wait()
    # 删除临时文件
    tmp_file.unlink()
    # 删除 ts 文件
    del_ts_cmd = f'del /Q "{ts_files}"'
    Popen(del_ts_cmd, shell=True, stdout=DEVNULL, stderr=DEVNULL).wait()
