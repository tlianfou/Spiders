# !/usr/bin/env python
# -*- coding:utf-8 -*-

from .__constant__ import *
from .settings import *
from . import utils
import threading
import openpyxl
import requests
import random
import time
import re
import os

requests_semaphore = threading.Semaphore(CONCURRENT_REQUESTS)
print_lock = threading.Lock()

video_serial = 0
serial_lock = threading.Lock()


def print_s(*args, sep=' ', end='\n', file=None):
    with print_lock:
        print(*args, end=end, sep=sep, file=file)


class BiliBili(object):
    def __init__(self):
        if not os.path.exists(ROOT_PATH):
            path = ''
            for i in ROOT_PATH.split('/'):
                path = '%s%s/' % (path, i)
                if not os.path.exists(path):
                    os.mkdir(path)

    # 获得封面图
    def get_cover(self, aid: str):
        video_response = SpiderCore.get_response(VIDEO_DEFAULT_URL % aid)

        cover_url = re.findall(r'<meta data-vue-meta="true" itemprop="image" content="(.*?)">',
                               video_response.text, re.S)
        if cover_url.__len__() == 0:
            print_s('get cover form aid: %s Failed' % aid)
            return
        cover_url = cover_url[0]
        print_s('cover_url: %s' % cover_url)

        cover_response = SpiderCore.get_response(cover_url)
        if (not (cover_response is None)) and cover_response.status_code != 200:
            print_s('access cover url: %s Failed!!!' % cover_url)
            return
        file_name = ('%s.%s' % (
            re.findall(r'<span class="tit">(.*?)</span>', video_response.text, re.S)[0],
            cover_url.split('/')[-1].split('.')[-1]))
        with open('%s/%s' % (ROOT_PATH, file_name), 'wb') as file:
            file.write(cover_response.content)

    # 获得弹幕
    def get_danmaku(self, aid: str):
        # 单个视频的response
        video_response = SpiderCore.get_response(API_DEFAULT_URL % (aid, MAIN_CID))
        if video_response.status_code != 200:
            print_s('access aid: %s Failed' % aid)
            return

        # 视频的访问码cid
        video_cid = re.findall(r'"cid":(.*?),', video_response.text, re.S)[0]

        # 获取标题
        title = re.findall(r'"title":"(.*?)"', video_response.text, re.S)[0]

        # 弹幕的response
        danmaku_response = SpiderCore.get_response(DANMAKU_DEFAULT_URL % video_cid)
        danmaku_response.encoding = 'utf-8'  # 修改编码方式为utf-8

        # 输出到文件
        # 直接输出源xml文件
        with open('%s/%s.xml' % (ROOT_PATH, title), mode='w', encoding='utf-8') as file:
            file.write(danmaku_response.text)

        # 仅输出所有弹幕，一行一个
        # danmaku_text = re.findall(r'">(.*?)</d>', danmaku_response.text, re.S)
        # with open('%s/%s.txt' % (self.__workspace, title), mode='w', encoding='utf-8') as file:
        #     for text in danmaku_text:
        #         file.write('%s\n' % text)

    # 获得视频播放量
    def get_views(self, aid: str, delay: int = 60, data_amount: int = 100):
        if data_amount < 1:
            print_s('data_amount must > 1')

        # 单个视频url
        video_response = SpiderCore.get_response(API_DEFAULT_URL % (aid, MAIN_CID))
        if video_response.status_code != 200:
            print_s('access aid: %s Failed' % aid)
            return

        print_s('Get the title of the video: av%s' % aid)
        title = re.findall(r'"title":"(.*?)"', video_response.text, re.S)[0]
        print_s('The title of the video: %s' % title)

        print_s('Create workbook: %s/%s_views.xlsx to storing data' % (ROOT_PATH, title))
        workbook_name = '%s_views.xlsx' % title
        utils.create_xl4views(ROOT_PATH, workbook_name)
        print_s('Complete...Begin to pull views...')

        # 提前获取和输出第一次获取的数据
        view = re.findall(r'"view":(.*?),', video_response.text, re.S)[0]
        utils.write2xl(ROOT_PATH, workbook_name, (utils.get_time(), int(view),))
        print_s('Views %s/%s: %s' % (1, data_amount, view))
        # 循环获取播放量
        for number in range(2, data_amount + 1):
            time.sleep(delay)
            video_response = SpiderCore.get_response(API_DEFAULT_URL % (aid, MAIN_CID))
            if video_response.status_code != 200:
                print_s('access number: %s Failed' % number)
                continue
            view = re.findall(r'"view":(.*?),', video_response.text, re.S)[0]
            print_s('Views %s/%s: %s' % (number, data_amount, view))
            utils.write2xl(ROOT_PATH, workbook_name, (utils.get_time(), int(view),))

    # 获取一个up主的所有视频
    def get_all_video(self, mid: str):
        # 获取个人空间的response (响应)
        space_response = SpiderCore.get_response(SPACE_DEFAULT_URL % (mid, PAGE_SIZE, 1))
        if space_response.status_code != 200:
            print_s('access mid: %s Failed' % mid)
            return
        author = re.findall(r'"name":"(.*?)"', SpiderCore.get_response(AUTHOR_DEFAULT_URL % mid).text, re.S)[0]
        count = int(re.findall('"count":(.*?),', space_response.text, re.S)[-1])

        if count == count / PAGE_SIZE:
            page_count = count / PAGE_SIZE
        else:
            page_count = int(count / PAGE_SIZE) + 1

        global video_serial
        video_serial = 0
        ScheduleThread(count).start()

        # 循环访问up主个人空间并处理
        threads = []
        for page_number in range(1, page_count + 1):
            threads.append(GetPageVideoThread(mid, PAGE_SIZE, page_number))
            threads[-1].start()
        for thread in threads:
            thread.join()
        print_s()
        time.sleep(5)  # 主动休息5秒防止风控

        author_workbook = openpyxl.Workbook()
        sheet = author_workbook.active
        sheet.title = 'Videos'
        sheet.append(('aid', 'title', 'view', 'danmaku', 'reply', 'favorite',
                      'coin', 'share', 'now_rank', 'his_rank', 'like'))
        for thread in threads:
            for result in thread.result:
                sheet.append(result)
        author_workbook.save('%s/%s_all_video.xlsx' % (ROOT_PATH, author))
        author_workbook.close()


class SpiderCore(object):
    session = requests.Session()
    session.headers = {
        'Referer': HOME_URL,
    }
    with open('bilibili.cookies', mode='r') as cookies_file:
        for cookie in cookies_file.read().split(';'):
            key, value = cookie.strip().split('=')
            session.cookies[key] = value

    @classmethod
    def get_response(cls, url: str):
        with requests_semaphore:
            time.sleep(random.randint(1, 2))
            while True:
                cls.session.headers['User-Agent'] = random.choice(USER_AGENTS)
                try:
                    return cls.session.get(url, timeout=30)
                except OSError or requests.exceptions.RequestException:
                    print_s('access url: %s Failed!!!  Retry... ' % url)
                    time.sleep(random.randint(1, 2))


class VideoMessageThread(threading.Thread):
    __slots__ = {'__aid', '__result'}

    def __init__(self, aid: str):
        threading.Thread.__init__(self)
        self.__aid = aid
        self.__result = []
        self.name = 'Thread-aid-%s' % aid

    def run(self):
        global video_serial
        global serial_lock

        # 单个视频的response
        video_response = SpiderCore.get_response(API_DEFAULT_URL % (self.__aid, MAIN_CID))
        # 状态码错误，访问失败
        if video_response.status_code != 200:
            print_s('\naccess video %s Failed' % self.__aid)
            return

        # 获取标题
        title = re.findall(r'"title":"(.*?)"', video_response.text, re.S)[0]
        # 获取状态  播放量、弹幕数
        status = re.findall(
            r'"stat":{"aid":.*?,"view":(.*?),"danmaku":(.*?),"reply":(.*?),"favorite":(.*?),"coin":(.*?),"share":(.*?),'
            r'"now_rank":(.*?),"his_rank":(.*?),"like":(.*?),"dislike":.*?,"evaluation":".*?"}',
            video_response.text, re.S)[0]
        self.__result.append(self.__aid)
        self.__result.append(title)
        for data in status:
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
        threads = []
        # 循环遍历每个视频
        for aid in aids:
            threads.append(VideoMessageThread(aid))
            threads[-1].start()
        for thread in threads:
            thread.join()
        for thread in threads:
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
            print_s('\rPull data: %f %%' % ((video_serial + 1) / self.__max_number * 100), end='')
            time.sleep(0.001)
