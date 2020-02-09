# !/usr/bin/env python
# -*- coding:utf-8 -*-
from .threads import *
import requests
import re
import os


class ImageSpider(object):
    __slots__ = {'__unit_title'}

    def __init__(self, unit_title: str = 'full'):
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
            title = re.findall(r'<title>#(.*?) - .*? - .*?</title>', illust_response.text, re.S)
            if title.__len__() == 0:
                title = 'default'
            else:
                title = legal_title(title[0])
            print_s('Use default title: ', title)
        else:
            title = legal_title(self.__unit_title)

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

    def get_illust(self, illust_id: str, is_unit: bool, file_name: str = None):
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
        illust_response = SpiderCore.get_response(ILLUST_DEFAULT_AJAX % illust_id)
        if illust_main_response is None or illust_response is None or (
                not (illust_main_response.status_code == 200 and illust_response.status_code == 200)):
            print_s('access illust_id: %s Failed' % illust_id)
            return
        # 获取作品标题并创建存放作品的文件夹
        location = self.__get_location(illust_main_response, is_unit)

        # 获取并处理所有image的链接
        images_url = get_images_url(illust_response)

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


class SearchSpider(object):
    __slots__ = {'keyword', 'total_page', 'min_bookmark', 'max_bookmark', 'download', 'mode'}

    def __init__(self, data_package: dir):
        self.keyword = data_package['keyword']
        self.total_page = data_package['total_page']
        self.min_bookmark = data_package['min_bookmark']
        self.max_bookmark = data_package['max_bookmark']
        self.download = data_package['download']
        self.mode = data_package['mode']
        if self.min_bookmark is None:
            self.min_bookmark = 0
        if self.max_bookmark is None:
            self.max_bookmark = 999999

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
        file_name = legal_title(re.findall(r'class="self">(.*?)</a>', bookmark_response.text, re.S)[0])
        if self.min_bookmark <= bookmark < self.max_bookmark:
            print_s('%s: https://www.pixiv.net/artworks/%s' % (file_name, illust_id))
            if self.download:
                image_spider = ImageSpider(self.keyword)
                image_spider.get_illust(illust_id, is_unit=True, file_name=file_name)

    def get_page(self, page_number: int):
        with PAGES_SEMAPHORE:
            response = SpiderCore.get_response(
                SEARCH_DEFAULT_AJAX % (self.keyword, self.keyword, page_number, self.mode))
            illust_ids = re.findall(r'"illustId":"(.*?)"', response.text.split('total')[0], re.S)
            threads = []
            for illust_id in illust_ids:
                threads.append(threading.Thread(target=self.get_bookmark, args=(illust_id,)))
                threads[-1].start()
            for thread in threads:
                thread.join()

    def run(self):
        threads = []
        for i in range(0, self.total_page):
            threads.append(threading.Thread(target=self.get_page, args=(i + 1,)))
            threads[-1].start()
        for thread in threads:
            thread.join()
