# !/usr/bin/env python
# -*- coding:utf-8 -*-
from .core import SpiderCore
from .middleware import *
import threading
import re

video_serial = 0


class VideoMessageThread(threading.Thread):
    __slots__ = {'__aid', '__result'}

    def __init__(self, aid: str):
        super(VideoMessageThread, self).__init__()
        self.__aid = aid
        self.__result = []
        self.name = 'Thread-aid-%s' % aid

    def run(self):
        global video_serial

        # 单个视频的response
        api_response = SpiderCore.get_response(API_DEFAULT_URL % (self.__aid, MAIN_CID))
        # 状态码错误，访问失败
        if api_response.status_code != 200:
            print_s('\naccess video %s Failed' % self.__aid)
            return

        # 获取标题
        title = re.findall(r'"title":"(.*?)"', api_response.text, re.S)
        # 获取状态  播放量、弹幕数
        status = re.findall(
            r'"stat":{"aid":.*?,"view":(.*?),"danmaku":(.*?),"reply":(.*?),"favorite":(.*?),"coin":(.*?),"share":(.*?),'
            r'"now_rank":(.*?),"his_rank":(.*?),"like":(.*?),"dislike":.*?,"evaluation":".*?"}',
            api_response.text, re.S)
        if title.__len__() <= 0 or status.__len__() <= 0:
            print('Get title and status Failed: %s' % self.name)
            return
        self.__result.append(self.__aid)
        self.__result.append(title[0])
        for data in status[0]:
            self.__result.append(int(data))
        with serial_lock:
            video_serial += 1

    @property
    def result(self):
        return self.__result


class GetPageVideoThread(threading.Thread):
    __slots__ = {'__mid', '__pagesize', '__page_number', '__result'}

    def __init__(self, mid: str, pagesize: int, page_number: int):
        threading.Thread.__init__(self)
        self.__mid = mid
        self.__pagesize = pagesize
        self.__page_number = page_number
        self.__result = []

    def run(self):
        # 获取个人空间的response (响应)
        space_response = SpiderCore.get_response(SPACE_DEFAULT_URL % (self.__mid, self.__pagesize, self.__page_number))
        # 状态码错误，访问失败
        if space_response.status_code != 200:
            print_s('\naccess space %d Failed' % self.__page_number)
            return

        # 获取本页所有的aid
        aids = re.findall(r'"aid":(.*?),"', space_response.text, re.S)
        thread_list = []
        # 循环遍历每个视频
        for aid in aids:
            thread_list.append(VideoMessageThread(aid))
            thread_list[-1].start()
        for thread in thread_list:
            thread.join()
        for thread in thread_list:
            self.__result.append(thread.result)

    @property
    def result(self):
        return self.__result


class ScheduleThread(threading.Thread):
    __slots__ = {'__max_number'}

    def __init__(self, max_number: int):
        threading.Thread.__init__(self)
        self.__max_number = max_number

    def run(self):
        global video_serial
        while video_serial < self.__max_number:
            with serial_lock:
                print_s('\rPull data: %f %%' % ((video_serial + 1) / self.__max_number * 100), end='')
            time.sleep(0.001)