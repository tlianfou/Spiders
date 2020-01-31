# !/usr/bin/env python
# -*- coding:utf-8 -*-

from .__constant__ import *
from .settings import *
from . import utils
import threading
import sys
import requests
import random
import time
import re
import os

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


def print_s(*args, sep=' ', end='\n', file=None):
    with PRINT_LOCK:
        print(*args, end=end, sep=sep, file=file)


def get_response_interface(url: str):
    return SpiderCore.get_response(url)


class Pixiv(object):
    def get_image(self, illust_id: str, file_name: str = None):
        """
        获得一个插图的图片
        :param illust_id: 作品id
        :param file_name: 存放的目录的名称，默认为作品名
        :return: None
        """
        pixiv = ImageSpider()
        pixiv.get_images(illust_id, True, file_name)

    def get_images(self, illust_ids: tuple or list or set, is_unit: bool = False):
        """
        获取多个作品的图片
        :param illust_ids: 作品id的集合
        :param is_unit: 是否统一放在工作目录下，默认为否，每个作品一个文件夹，文件夹名称为作品名
        :return: None
        """
        pixiv = ImageSpider()
        for illust_id in illust_ids:
            threading.Thread(target=pixiv.get_images, args=(illust_id, is_unit)).start()

    def get_ranking(self, mode: str = 'd'):
        """
        获取排行榜前50名的图片
        :param mode: 获取的排行榜以及存储的方式
            排行榜
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
            存储方式
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
        mode = utils.handle_mode(mode)
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
        pixiv = ImageSpider(unit_title=mode['mode'])
        number = 1
        # 多线程
        threads = []
        for illust_id in illust_ids:
            threads.append(
                threading.Thread(target=pixiv.get_images, args=(illust_id, mode['is_unit'], '%02d' % number)))
            threads[-1].start()
            number = number + 1

    def search(self, keyword: str, min_bookmark: int = None, max_bookmark: int = None, download: bool = False):
        if isinstance(min_bookmark, int) and isinstance(max_bookmark, int):
            if min_bookmark > 999999:
                print_s('min overflow')
            elif max_bookmark < min_bookmark:
                print_s('max must bigger than min')
                return
        total_response = SpiderCore.get_response(SEARCH_DEFAULT_URL % (keyword, keyword, 1))
        total = int(re.findall(r'"total":(.*?),', total_response.text, re.S)[0])
        if total / 60 == int(total / 60):
            total = int(total / 60)
        else:
            total = int(total / 60) + 1
        if total > 1000:
            total = 1000

        SearchSpider(
            {'keyword': keyword, 'total_page': total, 'min_bookmark': min_bookmark,
             'max_bookmark': max_bookmark, 'download': download}).run()


class SpiderCore(object):
    # session保存会话状态
    # headers是会话头
    # cookie是访问pixiv的关键，存放在 __constant__中
    session = requests.session()
    session.headers = DEFAULT_REQUEST_HEADERS
    if not os.access(COOKIES_PATH, os.R_OK):
        sys.stderr.write('Cannot open cookies file, please check it out')
        exit(1)
    with open(COOKIES_PATH, mode='r') as cookies_file:
        for cookie in cookies_file.read().split(';'):
            key, value = cookie.strip().split('=', 1)
            session.cookies[key] = value

    @classmethod
    def get_response(cls, main_url: str):
        """
        获取响应，最关键的函数
        :param main_url: 需要获取响应的url
        :return: 获取到的响应 或 None（在网络状况不佳 或 访问过多时）
        """
        time.sleep(random.randint(1, 3))
        with REQUESTS_SEMAPHORE:
            # for i in range(0, 5):
            while True:
                cls.session.headers['User-Agent'] = random.choice(USER_AGENTS)
                try:
                    return cls.session.get(main_url, timeout=30)
                except OSError or requests.exceptions.RequestException:
                    # print_s('access url: %s Failed!!!  Retry... ' % (main_url))
                    time.sleep(random.randint(1, 3))


class ImageSpider(object):
    __slots__ = {'__unit_title'}

    def __init__(self, unit_title: str = ''):
        """
        :param unit_title: 在联合保存时会用到的文件夹名称
        """
        self.__unit_title = unit_title

    def __get_location(self, illust_response: requests.Response, is_unit: bool):
        """
        获取作品放置的目录，在目录不存在时创建
        :param illust_response: 作品的响应
        :param is_unit: 是否统一放在同一目录下
        :return: 作品放置的目录
        """
        # 判断是否放在同一目录下，并获取文件夹title
        if not is_unit:
            title = re.findall(r'<title>#(.*?) - .*? - pixivSpider</title>', illust_response.text, re.S)
            if title.__len__() == 0:
                title = 'default'
            else:
                title = utils.legal_title(title[0])
            print_s('Use default title: ', title)
        else:
            title = self.__unit_title

        # 获取作品放置的目录并判断是否存在
        location: str = '%s/%s' % (ROOT_PATH, title)
        if os.path.exists(location):
            return location

        # 若目录不存在，则逐级构建
        path = ''
        for i in location.split('/'):
            path = '%s%s/' % (path, i)
            with DIR_LOCK:
                if not os.path.exists(path):
                    os.mkdir(path)
        return location

    def get_images(self, illust_id: str, is_unit: bool, file_name: str = None):
        """
        关键代码，获取image
        :param illust_id: 作品id
        :param is_unit: 是否放在同一目录下
        :param file_name: 存放作品的文件名，默认为illust_id
        :return: None
        """
        # 获取作品以及作品中images的请求的响应
        # 若获取失败则打印信息并直接返回
        illust_main_response = SpiderCore.get_response(ARTWORKS__DEFAULT_URL % illust_id)
        illust_response = SpiderCore.get_response(ILLUST_DEFAULT_URL % illust_id)
        if illust_main_response is None or illust_response is None or (
                not (illust_main_response.status_code == 200 and illust_response.status_code == 200)):
            print_s('access illust_id: %s Failed' % illust_id)
            return
        # 获取作品标题并创建存放作品的文件夹
        location = self.__get_location(illust_main_response, is_unit)

        # 获取并处理所有image的链接
        images_url = utils.get_images_url(illust_response)

        # 运用多线程输出图片
        number: int = 0  # 记录是第几个image
        threads = []  # 保存线程
        for image_url in images_url:
            # 自建线程ImageThread，传递一个dir作为数据package
            threads.append(ImageThread(
                {'illust_id': illust_id, 'image_url': image_url, 'location': location, 'file_name': file_name,
                 'number': number}))
            threads[-1].start()
            number = number + 1

        # 让上级线程中断在此防止判断是否成功时出错
        for thread in threads:
            thread.join()

        # 判断是否下载成功
        for thread in threads:
            if not thread.result:
                print_s('Do not complete download illust_id: %s !!!!' % illust_id)
        print_s('Complete download illust_id: %s !!!!' % illust_id)


class ImageThread(threading.Thread):
    __slots__ = {'__package', '__result'}

    def __init__(self, package: dir):
        """
        :param package: 数据包
                'illust_id': 作品id
                'image_url': 单个图片的url
                'location': 存放位置
                'file_name': 存放文件名
                'number': 作品中的第几张image
        """
        threading.Thread.__init__(self)
        self.__package = package
        self.__result: bool = True

    def run(self):
        # print_s('Download:page %s under word_id: %s and putting in directory: %s by thread: %s' % (
        #     self.__package['number'], self.__package['illust_id'], self.__package['location'],
        #     threading.current_thread().name))

        # 获取images的响应
        # 若获取失败则打印信息并直接返回
        image_response = SpiderCore.get_response(self.__package['image_url'])
        if image_response is None or image_response.status_code != 200:
            print_s('access %s\'s page: %s Failed' % (self.__package['illust_id'], self.__package['number']))
            self.__result = False
            return

        # 获取图片名称创建文件并输出
        with DISK_SEMAPHORE:
            if self.__package['file_name'] is None:
                with open('%s/%s' % (
                        self.__package['location'],
                        self.__package['image_url'].split('/')[-1].replace('_master1200', '')),
                          'wb') as image_file:
                    image_file.write(image_response.content)
            else:
                with open('%s/%s-%s.%s' % (
                        self.__package['location'], self.__package['file_name'], self.__package['number'],
                        self.__package['image_url'].split('.')[-1]), 'wb') as image_file:
                    image_file.write(image_response.content)

    @property
    def result(self):
        return self.__result


class SearchSpider(object):
    __slots__ = {'__keyword', '__total_page', '__min_bookmark', '__max_bookmark', '__download'}

    def __init__(self, data_package: dir):
        self.__keyword = data_package['keyword']
        self.__total_page = data_package['total_page']
        self.__min_bookmark = data_package['min_bookmark']
        self.__max_bookmark = data_package['max_bookmark']
        self.__download = data_package['download']
        if self.__min_bookmark is None:
            self.__min_bookmark = 0
        if self.__max_bookmark is None:
            self.__max_bookmark = 999999

    def get_bookmark(self, illust_id: str):
        """
        获取作品被收藏的数目
        :param illust_id: 作品id
        :return 作品被收藏的数目
        """
        bookmark_response = SpiderCore.get_response(BOOKMARK_DEFAULT_URL % illust_id)
        if bookmark_response.status_code != 200:
            print_s('access illust_id: %s Failed' % illust_id)
            return 0
        bookmark = re.findall(r'<i class="_icon _bookmark-icon-inline"></i>(.*?)</a>', bookmark_response.text, re.S)
        if bookmark.__len__() <= 0:
            return 0
        bookmark = int(bookmark[0])
        file_name = re.findall(r'class="self">(.*?)</a>', bookmark_response.text, re.S)[0]
        if self.__min_bookmark <= bookmark < self.__max_bookmark:
            print_s('%s: https://www.pixiv.net/artworks/%s' % (file_name, illust_id))
            if self.__download:
                pixiv = Pixiv()
                pixiv.get_image(illust_id, file_name=file_name)

    def get_page(self, page_number: int):
        with PAGES_SEMAPHORE:
            print_s('access page %s' % page_number)
            response = SpiderCore.get_response(SEARCH_DEFAULT_URL % (self.__keyword, self.__keyword, page_number))
            illust_ids = re.findall(r'"illustId":"(.*?)"', response.text.split('total')[0], re.S)
            threads = []
            for illust_id in illust_ids:
                threads.append(threading.Thread(target=self.get_bookmark, args=(illust_id,)))
                threads[-1].start()
            for thread in threads:
                thread.join()

    def run(self):
        for i in range(0, self.__total_page):
            threading.Thread(target=self.get_page, args=(i + 1,)).start()
