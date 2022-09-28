import json

import browser_cookie3
from requests.utils import dict_from_cookiejar, cookiejar_from_dict

from logger import logger
from settings import COOKIES_PATH, DOMAIN

if COOKIES_PATH.exists():
    cookies = json.loads(COOKIES_PATH.read_bytes())
    cookiejar = cookiejar_from_dict(cookies)
    logger.info("从保存的文件中获取登陆信息")
else:
    cookiejar = browser_cookie3.edge(domain_name=DOMAIN)
    cookies = dict_from_cookiejar(cookiejar)
    COOKIES_PATH.write_text(json.dumps(cookies, indent=4))
    logger.info("从浏览器中获取登陆信息")
