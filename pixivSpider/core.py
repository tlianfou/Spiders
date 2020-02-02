# !/usr/bin/env python
# -*- coding:utf-8 -*-

from .middleware import *
from .settings import *
import requests
import random
import time
import sys
import os


class SpiderCore(object):
    # session保存会话状态
    # headers是请求头
    # cookie是访问pixiv的关键，存放在文件中
    session = requests.session()
    session.headers = DEFAULT_REQUEST_HEADERS
    if not os.access(COOKIES_PATH, os.R_OK):
        sys.stderr.write('Cannot open cookies file, please check it out')
        exit(1)
    with open(COOKIES_PATH, mode='r') as cookies_file:
        for cookie in cookies_file.read().split(';'):
            key, value = cookie.strip().split('=', 1)
            session.cookies[key] = value

    if not os.path.exists(ROOT_PATH):
        # 若目录不存在，则逐级构建
        path = ''
        for i in ROOT_PATH.split('/'):
            path = '%s%s/' % (path, i)
            with DIR_LOCK:
                if not os.path.exists(path):
                    os.mkdir(path)

    @classmethod
    def get_response(cls, main_url: str):
        """
        获取响应，最关键的函数
        :param main_url: 需要获取响应的url
        :return: 获取到的响应 或 None（在网络状况不佳 或 访问过多时）
        """
        time.sleep(random.randint(1, DOWNLOAD_DELAY + 1))
        with REQUESTS_SEMAPHORE:
            # for i in range(0, 5):
            while True:
                cls.session.headers['User-Agent'] = random.choice(USER_AGENTS)
                try:
                    return cls.session.get(main_url, timeout=30)
                except OSError or requests.exceptions.RequestException:
                    # print_s('access url: %s Failed!!!  Retry... ' % main_url)
                    time.sleep(random.randint(1, DOWNLOAD_DELAY + 1))
