import asyncio
import re
from pathlib import Path
from uuid import uuid1

from downloader import download_single
from downloader_m3u8 import download_m3u8_raw
from logger import logger
from settings import COURSES_PATH, COOKIES_PATH
from apis import (
    get_download_url_from_course_url,
    get_download_urls,
    choose_course,
    choose_term,
    choose_chapters,
    get_course_by_cid,
    get_course_name,
    get_terms,
    get_chapters,
    get_courses_from_chapter
)


async def download_from_course_url(course_url, filename=None, path=None):
    """
    从课程链接进行下载
    @param course_url: 课程链接
    @param filename: 文件名
    @param path: 目录
    @return:
    """
    if not path:
        path = COURSES_PATH
    if not filename:
        filename = str(uuid1())

    urls = get_download_url_from_course_url(course_url, -1)
    if urls[1]:
        await download_single(urls[0], urls[1], filename, path)
    else:
        download_m3u8_raw(urls[0], path, filename, True)


async def download_from_selected_chapter(term_id, filename, chapter_name, courses, cid):
    tasks = []
    for course in courses:
        path = COURSES_PATH.joinpath(filename, chapter_name)
        course_name = course.get('name')
        file_id = course.get('resid_list')
        file_id = re.search(r'(\d+)', file_id).group(1)
        urls = get_download_urls(term_id, file_id, cid=cid)
        tasks.append(
            asyncio.create_task(
                download_single(
                    ts_url=urls[0], key_url=urls[1], filename=course_name, path=path
                )
            )
        )
    sem = asyncio.Semaphore(3)
    async with sem:
        await asyncio.wait(tasks)


def clear_cookies():
    """
    清除保存的 cookies 文件
    """
    if COOKIES_PATH.exists():
        COOKIES_PATH.unlink()


def main():
    menus = ["下载链接视频", "下载我的课程", "清除登录"]
    for i, menu in enumerate(menus):
        print(f"{i + 1}. {menu}")
    chosen = int(input('\n输入需要的功能：'))
    if chosen == 1:
        course_url = input('输入课程链接：')
        logger.info(f"course_url={course_url}")
        asyncio.run(download_from_course_url(course_url))
    elif chosen == 2:
        # 选择课程
        cid = choose_course()
        # 获取课程信息
        course = get_course_by_cid(cid)
        logger.info('获取课程信息成功')
        # 获取课程名称
        course_name = get_course_name(course)
        # 获取学期数据
        terms = get_terms(course)
        # 选择学期
        term = choose_term(terms)
        term_id = term.get('term_id')
        logger.info(f"课程: {course_name}({cid}), 学期ID: {term_id}")
        if input("是否下载所有章节:(输入任意值进入章节选择)") != "":
            # 选择章节
            chapters = choose_chapters(term)
        else:
            chapters = get_chapters(term)
        print("开始下载章节视频")
        for chapter in chapters:
            chapter_name = chapter.get('name').replace('/', '／').replace('\\', '＼')
            chapter_id = chapter.get("sub_id")
            chapter_name = f"{chapter_id + 1}.{chapter_name}"
            courses = get_courses_from_chapter(chapter)
            print(f"即将开始下载章节：{chapter_name} {courses[0].get('name')}")
            print('=' * 20)

            # 处理章节目录
            chapter_path = COURSES_PATH.joinpath(course_name, chapter_name)
            if not chapter_path.exists():
                chapter_path.mkdir(parents=True)

            asyncio.run(
                download_from_selected_chapter(
                    term_id, course_name, chapter_name, courses, cid
                )
            )
    elif chosen == 3:
        clear_cookies()
    else:
        print('请输入正确的序号！')


if __name__ == '__main__':
    main()
