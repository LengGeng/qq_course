import re
from uuid import uuid1

from logger import logger
from settings import COURSES_PATH, COOKIES_PATH
from apis import (
    choose_course,
    choose_term,
    choose_chapters,
    get_course_by_cid,
    get_course_name,
    get_terms,
    get_chapters,
    get_courses_from_chapter,
    parse_course_url,
    get_m3u8_url,
    download_course
)


def download_from_course_url(course_url, filename=None, path=None):
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

    cid, term_id, file_id = parse_course_url(course_url)

    m3u8_url = get_m3u8_url(cid, term_id, file_id)
    download_course(m3u8_url, cid, term_id, path.joinpath(f"{filename}.mp4"))


def download_from_selected_chapter(cid, term_id, tasks, chapter_path):
    """
    从选择的章节进行下载
    @param cid: 课程ID
    @param term_id: 学期ID
    @param tasks: 任务列表
    @param chapter_path: 章节目录
    @return:
    """
    for task in tasks:
        # 任务名
        task_name = task.get('name')
        # 判断类型
        task_type = task.get("type")
        # 2: 视频,3: 附件
        if task_type == 2:
            file_id = task.get('resid_list')
            file_id = re.search(r'(\d+)', file_id).group(1)
            m3u8_url = get_m3u8_url(cid, term_id, file_id)
            filename = task_name.replace('/', '／').replace('\\', '＼')
            filepath = chapter_path.joinpath(f"{filename}.mp4")
            # 判断是否下载过
            if filepath.exists():
                print(f"{filepath} 已存在！")
                continue
            download_course(m3u8_url, cid, term_id, filepath)
        else:
            print(f"{task_name} 类型暂不支持下载")


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
        download_from_course_url(course_url)
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
            tasks = get_courses_from_chapter(chapter)
            print('=' * 50)
            print(f"即将开始下载章节：{chapter_name}")

            # 处理章节目录
            chapter_path = COURSES_PATH.joinpath(course_name, chapter_name)
            if not chapter_path.exists():
                chapter_path.mkdir(parents=True)

            download_from_selected_chapter(
                cid, term_id, tasks, chapter_path
            )
    elif chosen == 3:
        clear_cookies()
    else:
        print('请输入正确的序号！')


if __name__ == '__main__':
    main()
