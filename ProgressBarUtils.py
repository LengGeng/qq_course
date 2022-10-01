import time

from utils import size_format


class DownloaderProgressBar:
    def __init__(self, filename: str, total: int, width: int = 30):
        """
        下载器进度条
        @param filename: 文件名
        @param total: 文件大小
        @param width: 进度条长度
        """
        self.entity_symbol = '■'
        self.empty_symbol = '□'

        self.total = total
        self.total_format = size_format(self.total)
        self.width = width
        self.filename = filename
        self.progress = 0
        self.speed = 0
        self.timer = time.time()
        self.update_time = self.timer
        self.finished = False

        print(f"Downloading {self.filename} ({self.total_format})")

    def print_bar(self):
        """打印进度条"""
        left = int(self.width * self.progress // self.total)
        right = self.width - left
        percent = self.progress / self.total * 100
        print(
            f'\r{percent:>2.0f}%',
            f"[{self.entity_symbol * left}{self.empty_symbol * right}]",
            f"[{size_format(self.progress)}/{self.total_format}, {size_format(self.speed)}/s]",
            end='',
            flush=True,
        )

    def finish(self):
        """打印下载完成信息"""
        self.finished = True
        time_cost = time.time() - self.timer
        info = f"(time cost:{time_cost:.1f}s,average speed:{size_format(int(self.total / time_cost))}/s)"
        print(f"\nDownloaded  {self.filename} {info}")

    def update(self, progress, interval=None):
        """
        更新进度
        @param progress: 新进度
        @param interval: 距离上次更新的时间间隔(用于计算下载速度),默认使用 time() 函数获取
        @return:
        """
        if self.finished:
            return
        if interval is None:
            update_time = time.time()
            interval = update_time - self.update_time
        else:
            update_time = self.update_time + interval

        incremental = progress - self.progress
        self.speed = int(incremental / interval)
        self.progress = min(progress, self.total)
        self.update_time = update_time

        self.print_bar()
        if progress >= self.total:
            self.finish()

    def addition(self, incremental, interval=None):
        """
        增量进度
        @param incremental: 增加的进度(是一个增加量,不是新进度)
        @param interval: 距离上次更新的时间间隔(用于计算下载速度),默认使用 time() 函数获取
        @return:
        """
        progress = self.progress + incremental
        self.update(progress, interval)


def main():
    import random

    size = 1024 * 1024
    bar = DownloaderProgressBar("测试文件.txt", size)
    incremental = 1024 * 10
    while not bar.finished:
        time.sleep(0.2)
        bar.addition(random.randint(incremental, incremental * 5))

    bar.addition(random.randint(incremental, incremental * 5))


if __name__ == '__main__':
    main()
