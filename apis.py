import base64
import json
import re
from urllib.parse import parse_qs, urlparse

import requests

import urls
from cookies import cookiejar, cookies
from logger import logger
from settings import DEFAULT_HEADERS, PROXIES, CURRENT_USER, COOKIES_PATH, CACHE_PATH
from utils import parse_page


def get_course_by_cid(cid):
    """
    获取课程信息
    @param cid: 课程ID
    @return: 课程信息
    """
    url = urls.BasicInfoUri.format(cid=cid)
    response = requests.get(url, headers=DEFAULT_HEADERS, proxies=PROXIES)

    response_json = response.json()
    with CACHE_PATH.joinpath(f"{cid}.json").open('w') as f:
        json.dump(response_json, f, ensure_ascii=False, indent=4)

    return response_json


def get_all_courses():
    """
    获取用户所有的课程
    @return: 课程信息列表
    """

    def add_courses_form_response(res):
        """
        解析响应中的课程添加到课程列表中
        @param res: response
        @return:
        """
        if res:
            for i in res.get('map_list'):
                for j in i.get('map_courses'):
                    courses.append({
                        'name': j.get('cname'),
                        'cid': j.get('cid')
                    })

    courses = []
    page = 1
    response = None
    # response.end != 0 代表有没有下一页
    while page == 1 or response.get('end') == 0:
        # count 参数最多为 10
        response = requests.get(urls.CourseList,
                                params={'page': page, 'count': '10'},
                                headers=DEFAULT_HEADERS,
                                cookies=cookiejar,
                                proxies=PROXIES).json().get('result')
        add_courses_form_response(response)
        page += 1
    return courses


def choose_course():
    """
    从账号下的所有课程中选择要下载的课程
    @return: 选择的课程ID
    """
    courses = get_all_courses()
    print('你的账号里有如下课程：')
    for i, course in enumerate(courses):
        print(f"{i + 1}. {course.get('name')}")
    index = int(input('请输入要下载的课程序号(回车结束)：'))
    cid = courses[index - 1].get('cid')
    return cid


def get_course_name(course):
    """
    从课程信息中获取课程名
    @param course: 课程信息
    @return: 课程名
    """
    return (
        course.get('result')
            .get('course_detail')
            .get('name')
            .replace('/', '／')
            .replace('\\', '＼')
    )


def get_terms_from_api(cid, term_id_list):
    """
    请求获取学期信息
    @param cid: 课程ID
    @param term_id_list: 学期ID数组,里面是整数格式的 term_id
    @return:
    """
    params = {'cid': cid, 'term_id_list': term_id_list}
    response = requests.get(urls.ItemsUri, params=params, headers=DEFAULT_HEADERS, proxies=PROXIES).json()
    return response


def get_terms(course):
    """
    从课程信息内获取学期信息
    @param course: 课程信息
    @return: 学期信息
    """
    course = course.get('result')
    if course.get('course_detail'):
        terms = course.get('course_detail').get('terms')
    else:
        terms = course.get('terms')
    return terms


def choose_term(terms):
    """
    选择学期
    @param terms: 学期信息
    @return: 选择的学期信息
    """
    index = 1
    if len(terms) > 1:
        for i, term in enumerate(terms):
            print(f"{i + 1}. {term.get('name')}")
        index = int(input('请选择学期：'))
    term = terms[index - 1]
    return term


def get_chapters(term):
    return term.get('chapter_info')[0].get('sub_info')


def choose_chapters(term):
    """
    选择章节
    @param term: 学期信息
    @return: 选择的章节信息列表
    """
    chapters = get_chapters(term)
    for i, chapter in enumerate(chapters):
        print(f"{i + 1}. {chapter.get('name')}")
    chapter_pages = parse_page(input('请选择章节：页码(1)或页码范围(1-5)多个可以使用逗号(,)分隔'))
    selected_chapters = []
    for chapter_page in chapter_pages:
        # 判断页码是否合法
        chapter_page -= 1
        if 0 <= chapter_page < len(chapters):
            selected_chapters.append(chapters[chapter_page])
    return selected_chapters


def get_courses_from_chapter(chapter):
    return chapter.get('task_info')


def get_token_for_key_url(term_id, cid):
    """
    这个 key_url 后面要接一个 token,研究发现，token 是如下结构 base64 加密后得到的
    其中的 plskey 是要填的，这个东西来自登陆时的 token 去掉结尾的两个 '='，也可以在 cookies.json 里获取
    """
    if not CURRENT_USER:
        uin = get_uin()
        CURRENT_USER['uin'] = uin
        if len(uin) > 10:
            # 微信
            CURRENT_USER['ext'] = cookies.get('uid_a2')
            CURRENT_USER['appid'] = cookies.get('uid_appid')
            CURRENT_USER['uid_type'] = cookies.get('uid_type')
            str_token = 'uin={uin};skey=;pskey=;plskey=;ext={uid_a2};uid_appid={appid};' \
                        'uid_type={uid_type};uid_origin_uid_type=2;uid_origin_auth_type=2;' \
                        'cid={cid};term_id={term_id};vod_type=0;platform=3' \
                .format(uin=uin,
                        uid_a2=CURRENT_USER.get('ext'),
                        appid=CURRENT_USER.get('appid'),
                        uid_type=CURRENT_USER.get('uid_type'),
                        cid=cid,
                        term_id=term_id)
        else:
            # skey = pskey = plskey = None
            CURRENT_USER['p_lskey'] = cookies.get('p_lskey')
            CURRENT_USER['skey'] = cookies.get('skey')
            CURRENT_USER['pskey'] = cookies.get('p_skey')
            str_token = 'uin={uin};skey={skey};pskey={pskey};plskey={plskey};ext=;uid_type=0;' \
                        'uid_origin_uid_type=0;uid_origin_auth_type=0;cid={cid};term_id={term_id};' \
                        'vod_type=0' \
                .format(uin=uin,
                        skey=CURRENT_USER.get('skey'),
                        pskey=CURRENT_USER.get('pskey'),
                        plskey=CURRENT_USER.get('plskey'),
                        cid=cid,
                        term_id=term_id)
        CURRENT_USER['token'] = str_token

    # 直接从 CURRENT_USER 里读取参数
    logger.info(CURRENT_USER)
    return base64.b64encode(CURRENT_USER.get('token').encode()).decode()[:-2]


def get_key_url_from_m3u8(m3u8_url):
    """
    从 m3u8 url 中获取秘钥链接
    @param m3u8_url: 带有 sign,t,us 参数的 m3u8 下载链接
    @return: 秘钥链接
    """
    m3u8_text = requests.get(m3u8_url, proxies=PROXIES).text
    pattern = re.compile(r'(https://ke.qq.com/cgi-bin/qcloud/get_dk.+)"')
    return pattern.findall(m3u8_text)[0]


def get_video_url(video_info, video_index=-1, cid=None, term_id=None):
    """
    根据视频信息获取对应的视频及秘钥链接
    @param video_info: 视频信息
    @param video_index: 清晰度选择索引 -1为最后一项,清晰度最高
    @param cid: 课程ID
    @param term_id: 学期ID
    @return:
    """
    video = video_info.get('videoInfo').get('transcodeList', None)
    if video:
        # 根据 video_index 选择对应清晰度的视频下载链接
        video = video[video_index]
        # 视频地址
        video_url = video.get('url').replace('.m3u8', '.ts')
        # 秘钥地址,没有则是不需要解密
        key_url = (
                get_key_url_from_m3u8(video.get('url'))
                + '&token='
                + get_token_for_key_url(term_id=term_id, cid=cid)
        )
        return video_url, key_url
    return video_info.get('videoInfo').get('sourceVideo').get('url'), None


def get_video_info(file_id, t, sign, us):
    """
    1258712167 这个跟请求的 cdn 有关
    但我发现这东西写死在 js 里，且不同账户下不同课程都是用这一个 cdn
    而且这东西没有通过 api 数据返回，初步判断它是固定的
    因此将其作为固定参数
    """
    url = urls.MediaUri + str(file_id)
    params = {'t': t, 'sign': sign, 'us': us, 'exper': 0}
    response = requests.get(url, params=params, cookies=cookiejar, proxies=PROXIES).json()
    return response


def get_video_token(term_id, file_id):
    """
    获取访问 m3u8 的 token 的参数
    @param term_id: term_id
    @param file_id: file_id
    @return: sign,t,us(用来获取视频m3u8)
    """
    params = {'term_id': term_id, 'fileId': file_id}
    response = requests.get(
        urls.TokenUri, params=params, cookies=cookiejar, proxies=PROXIES
    ).json()
    return response.get('result')


def parse_cid_url(course_url):
    """
    解析课程ID
    @param course_url: 课程链接
    @return: 课程ID
    """
    pattern = re.compile('https://ke.qq.com/webcourse/(.*)/')
    return pattern.findall(course_url)[0]


def parse_course_url(course_url):
    """
    解析课程链接
    @param course_url: 课程链接
    @return: 获取 token 要用的 file_id 和 term_id
    """
    file_id = parse_qs(course_url).get('vid')[0]
    term_id = urlparse(course_url).path.split('/')[-1]
    return term_id, file_id


def get_download_url_from_course_url(course_url, video_index=-1):
    """
    从课程链接中解析出需要下载的视频地址
    @param course_url: 课程链接
    @param video_index: 清晰度
    @return: 视频链接
    """
    term_id, file_id = parse_course_url(course_url)
    cid = parse_cid_url(course_url)
    tokens = get_video_token(term_id, file_id)
    video_info = get_video_info(
        file_id, tokens.get('t'), tokens.get('sign'), tokens.get('us')
    )
    return get_video_url(video_info, video_index, cid=cid, term_id=term_id)


def get_download_urls(term_id, file_id, video_index=-1, cid=None):
    tokens = get_video_token(term_id, file_id)
    video_info = get_video_info(
        file_id, tokens.get('t'), tokens.get('sign'), tokens.get('us')
    )
    return get_video_url(video_info, video_index, cid=cid, term_id=term_id)


def get_video_rec(cid, file_id, term_id, video_index=0):
    # 腾讯课堂现在强制绑定手机号，看样子是更新了
    # 新发现的接口，疑似wechat / qq通用，无需cookie，只要uin
    # 返回dk( ts文件密匙 )，视频文件链接，时长，生存时间，字幕等信息
    # 这里返回的rec_video_info.info里面含有不同清晰度的视频文件，越清晰的排序越靠前
    params = {
        'course_id': cid,
        'file_id': file_id,
        'term_id': term_id,
        'header': '{{"srv_appid":201,"cli_appid":"ke","uin":"{}","cli_info":{{"cli_platform":3}}}}'.format(get_uin())
    }
    response = requests.get(urls.VideoRec, headers=DEFAULT_HEADERS, params=params, proxies=PROXIES).json()
    if response:
        info = response.get('result').get('rec_video_info')
        ts_url = info.get('infos')[video_index].get('url').replace('.m3u8', '.ts')
        key = info.get('dk')
        return ts_url, key


def get_course_url(course):
    """
    拼接课程链接
    @param course: 课程字典
    @return:
    """
    cid = course.get('cid')
    term_id = course.get('term_id')
    course_id = course.get('taid')
    url = 'https://ke.qq.com/webcourse/{}/{}#taid={}&vid={}'.format(
        cid, term_id, course_id, course.get('resid_list')
    )
    return url


def get_uin():
    response = requests.get(urls.DefaultAccount,
                            cookies=cookiejar,
                            headers=DEFAULT_HEADERS,
                            proxies=PROXIES).json()
    if response.get('retcode') == 0:
        return response.get('result').get('tiny_id')
    return input('请输入你的QQ号 / 微信uin(回车结束)：')
