# !/usr/bin/env python
# -*- coding:utf-8 -*-
import os

# settings for bilibiliSpider project

# The root directory where the results are stored
# Created automatically if it doesn't exist
ROOT_PATH = './default'

# This option is used to store the path of your cookies file
COOKIES_PATH = os.path.join(os.path.dirname(__file__), 'bilibili.cookies')

# The default request headers:
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-cn, zh;q=0.9',
    'Referer': 'https://www.bilibili.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/79.0.3945.130 Safari/537.36',
}

# Configure a maximum delay for requests for the same website (default: 3)
DOWNLOAD_DELAY = 3

# Configure maximum concurrent requests performed by spider
# default and recommended: 25
CONCURRENT_REQUESTS = 25

# Number of videos displays on the home page of an up master
# default and recommended: 50
PAGE_SIZE = 50
