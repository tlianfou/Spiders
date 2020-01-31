# !/usr/bin/env python
# -*- coding:utf-8 -*-
from . import spiders
from .threads import *
import re


def get_illust(illust_id: str, file_name: str = None):
    """
    get the images from an illust
    :param illust_id: 作品id
    :param file_name: 存放的目录的名称，默认为作品名
    :return: None
    """
    pixiv = spiders.ImageSpider()
    pixiv.get_illust(illust_id, True, file_name)


def get_illusts(illust_ids: tuple or list or set, is_unit: bool = False):
    """
    获取多个作品的图片
    :param illust_ids: 作品id的集合
    :param is_unit: 是否统一放在工作目录下，默认为否，每个作品一个文件夹，文件夹名称为作品名
    :return: None
    """
    threads = []
    pixiv = spiders.ImageSpider()
    for illust_id in illust_ids:
        threads.append(threading.Thread(target=pixiv.get_illust, args=(illust_id, is_unit)))
        threads[-1].start()
    for thread in threads:
        thread.join()


def get_ranking(mode: str = 'd'):
    """
    获取排行榜前50名的图片
    :param mode: 获取的排行榜以及存储的方式
        ranking
        ========= ===============================================================
        Character Meaning
        --------- ---------------------------------------------------------------
        'd'       daily: 每日排行榜, default
        'w'       weekly: 每周排行榜
        'm'       monthly: 每月排行榜
        'n'       rookie: 新人排行榜
        'o'       original: 原创排行榜
        'a'       male: 受男性喜欢排行榜
        'f'       female: 受女性喜欢排行榜
        'r'       r-18: attach-mode
        ========= ===============================================================
        store mode
        ========= ===============================================================
        Character Meaning
        --------- ---------------------------------------------------------------
        'u'       unit: 联合存储，所有作品共享同一个文件夹, default
        's'       split: 分裂存储，每个作品一个文件夹
        ========= ===============================================================
        eg. 'du', 'ud', 'd', 'u', ''均代表每日排行榜并且存储进同一个文件夹
    :return: None
    """
    # 处理并获取mode
    mode = handle_mode(mode)
    if mode is None:
        print_s('Mode error')
        return

    # 获得排行榜响应
    ranking_response = SpiderCore.get_response(RANKING_DEFAULT_URL % mode['mode'])
    if not ranking_response.status_code == 200:
        print_s('get ranking in mode: %s Failed' % mode)
        return

    # 获得排行榜中作品的id
    illust_ids = re.findall(r'data-id="(.*?)"', ranking_response.text, re.S)
    illust_ids = sorted(set(illust_ids), key=illust_ids.index)

    # get_image
    pixiv = spiders.ImageSpider(unit_title=mode['mode'])
    # 多线程
    threads = []
    for illust_id in illust_ids:
        threads.append(
            threading.Thread(target=pixiv.get_illust, args=(illust_id, mode['is_unit'], '%02d' % (len(threads) + 1))))
        threads[-1].start()
    for thread in threads:
        thread.join()


def search(keyword: str, min_bookmark: int = None, max_bookmark: int = None, download: bool = False):
    if isinstance(min_bookmark, int) and isinstance(max_bookmark, int):
        if min_bookmark > 999999:
            print_s('min overflow')
        elif max_bookmark < min_bookmark:
            print_s('max must bigger than min')
            return
    total_response = SpiderCore.get_response(SEARCH_DEFAULT_AJAX % (keyword, keyword, 1))
    total = int(re.findall(r'"total":(.*?),', total_response.text, re.S)[0])
    if total / SEARCH_PAGE_SIZE == int(total / SEARCH_PAGE_SIZE):
        total = int(total / SEARCH_PAGE_SIZE)
    else:
        total = int(total / SEARCH_PAGE_SIZE) + 1
    if total > 1000:
        total = 1000
    print('total: %s' % total)
    spiders.SearchSpider(
        {'keyword': keyword, 'total_page': total, 'min_bookmark': min_bookmark,
         'max_bookmark': max_bookmark, 'download': download}).run()
