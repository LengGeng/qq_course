from pathlib import Path
from urllib.request import getproxies

COOKIES_PATH = Path('cookies.json')
COURSES_PATH = Path('courses')
CACHE_PATH = Path('cache')

# 检查目录是否存在,不存在则创建
if not COURSES_PATH.exists():
    COURSES_PATH.mkdir()
if not CACHE_PATH.exists():
    CACHE_PATH.mkdir()

DOMAIN = "ke.qq.com"
DEFAULT_HEADERS = {'referer': 'https://ke.qq.com/webcourse/'}
CURRENT_USER = {}
PROXIES = getproxies()  # 避免当你使用魔法时出现 check_hostname requires server_hostname
