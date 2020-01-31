# !/usr/bin/env python
# -*- coding:utf-8 -*-
from .core import SpiderCore
from .middleware import *
import threading


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
        super(ImageThread, self).__init__()
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
