# !/usr/bin/env python
# -*- coding:utf-8 -*-

# settings for pixivSpider project
from .__constant__ import API_URL

# The root directory where the results are stored
# Created automatically if it doesn't exist
ROOT_PATH = './default'

# This option is used to store the path of your cookies file
COOKIES_PATH = './pixiv.cookies'

# The default request headers:
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-cn, zh;q=0.9, en-gb;q=0.8, en;q=0.7',
    'Referer': API_URL,
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/79.0.3945.130 Safari/537.36',
}

# Configure maximum concurrent requests performed by spider
# default and recommended: 200
CONCURRENT_REQUESTS = 200

# Configure maximum concurrent access search page by spider
# default and recommended: 200
CONCURRENT_SEARCH_PAGES = 200

# Configure maximum concurrent access disk by spider
# default and recommended: 400
CONCURRENT_DISK_ACCESS = 400

# Number of videos displays on the home page of an up master
# default and recommended: 50
PAGE_SIZE = 50
