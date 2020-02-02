# !/usr/bin/env python
# -*- coding:utf-8 -*-

from .middleware import *
from .settings import *
import requests
import random
import time


class SpiderCore(object):
    session = requests.Session()
    session.headers = {
        'Referer': HOME_URL,
    }
    with open(COOKIES_PATH, mode='r') as cookies_file:
        for cookie in cookies_file.read().split(';'):
            key, value = cookie.strip().split('=')
            session.cookies[key] = value

    if not os.path.exists(ROOT_PATH):
        path = ''
        for i in ROOT_PATH.split('/'):
            path = '%s%s/' % (path, i)
            if not os.path.exists(path):
                os.mkdir(path)

    @classmethod
    def get_response(cls, url: str, **kwargs):
        with requests_semaphore:
            time.sleep(random.randint(1, DOWNLOAD_DELAY))
            while True:
                cls.session.headers['User-Agent'] = random.choice(USER_AGENTS)
                try:
                    return cls.session.get(url, timeout=30, **kwargs)
                except OSError or requests.exceptions.RequestException:
                    print_err('access url: %s Failed!!!  Retry... \n' % url)
                    time.sleep(random.randint(1, DOWNLOAD_DELAY))
