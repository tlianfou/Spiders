# !/usr/bin/env python
# -*- coding:utf-8 -*-
import re
import requests
import threading
from .settings import *

SEARCH_PAGE_SIZE = 60

# requests的信号量，用于限制网络访问的线程数
REQUESTS_SEMAPHORE = threading.Semaphore(CONCURRENT_REQUESTS)
# 文件访问的信号量，用于限制磁盘访问的线程数
DISK_SEMAPHORE = threading.Semaphore(CONCURRENT_DISK_ACCESS)
# 搜索时页面访问信号量，控制访问page的线程数目
PAGES_SEMAPHORE = threading.Semaphore(CONCURRENT_SEARCH_PAGES)
# 文件夹访问信号量，控制文件夹只能由一个线程创建
DIR_LOCK = threading.Lock()
# 控制台打印信号量，print只能有一个线程
PRINT_LOCK = threading.Lock()

HOME_URL = 'http://www.pixiv.net'

RANKING_DEFAULT_URL = 'https://www.pixiv.net/ranking.php?mode=%s'

BOOKMARK_DEFAULT_URL = 'https://www.pixiv.net/bookmark_detail.php?illust_id=%s'

API_URL = 'https://app-api.pixiv.net/'

ARTWORKS__DEFAULT_URL = 'https://www.pixiv.net/artworks/%s'

ILLUST_DEFAULT_AJAX = 'https://www.pixiv.net/ajax/illust/%s/pages'

SEARCH_DEFAULT_AJAX = 'https://www.pixiv.net/ajax/search/artworks/' \
                      '%s?word=%s&order=date_d&p=%s&mode=%s&s_mode=s_tag&type=all'

USER_AGENTS = [
    'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.28.3 (KHTML, like Gecko) '
    'Version/3.2.3 ChromePlus/4.0.222.3 Chrome/4.0.222.3 Safari/525.28.3',
    'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/532.2 (KHTML, like Gecko) '
    'ChromePlus/4.0.222.3 Chrome/4.0.222.3 Safari/532.2',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML like Gecko) '
    'Chrome/51.0.2704.79 Safari/537.36 Edge/14.14931',
    'Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) '
    'Version/6.0 Mobile/10A5355d Safari/8536.25',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) '
    'Version/7.0.3 Safari/7046A194A',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/79.0.3945.130 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/44.0.2403.155 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:64.0) Gecko/20100101 Firefox/64.0',
    'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:63.0) Gecko/20100101 Firefox/63.0',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko'
]


def print_s(*args, sep=' ', end='\n', file=None):
    with PRINT_LOCK:
        print(*args, end=end, sep=sep, file=file)


def get_images_url(illust_response: requests.Response):
    """获取并处理每个图片的url"""
    images_url = re.findall(r'"regular":"(.*?)"', illust_response.text, re.S)
    for i in range(0, images_url.__len__()):
        images_url[i] = images_url[i].replace(r'\/', '/')
    return images_url


def legal_title(title: str):
    return title.replace('/', '-').replace('\\', '-').replace(':', '：'). \
        replace('?', '？').replace('"', '”').replace('<', '＜'). \
        replace('>', '＞').replace('|', '丨')


def legal_mode(mode):
    if 'u' in mode and 's' in mode:
        return False
    if 'r' in mode:
        if 'm' in mode or 'n' in mode or 'o' in mode:
            return False
    for element in {'u', 's', 'r'}:
        try:
            mode.remove(element)
        except ValueError:
            pass
    if mode.__len__() <= 1:
        return True
    else:
        return False


def handle_mode(mode: str):
    mode = sorted(set(mode), key=mode.index)
    if not legal_mode(mode.copy()):
        return None

    ranking_dir = {
        'd': 'daily',
        'w': 'weekly',
        'm': 'monthly',
        'n': 'rookie',
        'o': 'original',
        'a': 'male',
        'f': 'female'
    }
    ranking_mode: dir = {'is_unit': True, 'mode': 'daily', 'r-18': False}

    for element in mode:
        if element == 'u':
            ranking_mode['is_unit'] = True
        elif element == 's':
            ranking_mode['is_unit'] = False
        elif element == 'r':
            ranking_mode['r-18'] = True
        else:
            ranking_mode['mode'] = ranking_dir[element]

    if ranking_mode['r-18']:
        ranking_mode['mode'] = '{}_r18'.format(ranking_mode['mode'])
    return ranking_mode
