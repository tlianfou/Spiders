# !/usr/bin/env python
# -*- coding:utf-8 -*-
from .settings import *
from .threads import *
from . import threads
import lxml.etree
import subprocess
import json
import re


# 获得封面图
def get_cover(aid: str):
    api_response = SpiderCore.get_response(API_DEFAULT_URL % aid)
    if api_response.status_code != 200:
        print_err('access video av%s Failed' % aid)

    api_json = api_response.json()
    title = get_title(api_json)
    cover_url = get_cover_url(api_json)
    if cover_url is None:
        print_err('Get cover url form aid: %s Failed\n' % aid)
        return

    cover_response = SpiderCore.get_response(cover_url)
    if cover_response is None or cover_response.status_code != 200:
        print_err('Access cover url: %s Failed!!!\n' % cover_url)
        return
    file_name = ('%s/%s.%s' % (ROOT_PATH, title, cover_url.split('.')[-1]))
    with open(file_name, 'wb') as file:
        file.write(cover_response.content)


# 获得弹幕
def get_danmaku(aid: str):
    # 单个视频的response
    api_response = SpiderCore.get_response(API_DEFAULT_URL % aid)
    if api_response.status_code != 200:
        print_err('access aid: %s Failed\n' % aid)
        return

    api_json = api_response.json()
    # 视频的标题和访问码cid
    title = get_title(api_json)
    video_cid = get_video_cid(api_json)
    if video_cid is None:
        print_err('Get video cid from aid: %s Failed\n' % aid)
        return

        # 弹幕的response
    danmaku_response = SpiderCore.get_response(DANMAKU_DEFAULT_URL % video_cid)
    if danmaku_response.status_code != 200:
        print_err('Get danmaku from aid: %s Failed\n' % aid)
        return
    danmaku_response.encoding = 'utf-8'  # 修改编码方式为utf-8

    # 输出到文件
    # 直接输出源xml文件
    with open('%s/%s.xml' % (ROOT_PATH, title), mode='wb') as file:
        element = lxml.etree.fromstring(danmaku_response.text.encode(encoding='utf-8'))
        file.write(lxml.etree.tostring(element_or_tree=element, encoding='utf-8', pretty_print=True))

    # 仅输出所有弹幕，一行一个
    # danmaku_text = re.findall(r'">(.*?)</d>', danmaku_response.text, re.S)
    # with open('%s/%s.txt' % (ROOT_PATH, title), mode='w', encoding='utf-8') as file:
    #     for text in danmaku_text:
    #         file.write('%s\n' % text)


# 获得视频播放量
def get_views(aid: str, delay: int = 60, data_amount: int = 100):
    if data_amount < 1:
        print_err('Data amount must > 1\n')
        return

    # 单个视频response
    api_response = SpiderCore.get_response(API_DEFAULT_URL % aid)
    if api_response.status_code != 200:
        print_err('Access aid: %s Failed\n' % aid)
        return

    api_json = api_response.json()
    title = get_title(api_json)

    print_s('Create workbook: %s/%s_views.xlsx to storing data' % (ROOT_PATH, title))
    workbook_name = '%s_views.xlsx' % title
    create_xl4views(ROOT_PATH, workbook_name)
    print_s('Complete...Begin to pull views...')

    # 提前获取和输出第一次获取的数据
    view = get_view(api_json)
    if view is None:
        print_err('Get view from aid: %s Failed\n' % aid)
    write2xl(ROOT_PATH, workbook_name, (get_time(), view,))
    print_s('Views %s/%s: %s' % (1, data_amount, view))

    # 循环获取播放量
    for number in range(2, data_amount + 1):
        time.sleep(delay)
        api_response = SpiderCore.get_response(API_DEFAULT_URL % aid)
        if api_response.status_code != 200:
            print_err('access number: %s Failed\n' % number)
            continue

        api_json = api_response.json()
        view = get_view(api_json)
        if view is None:
            print_err('Get view from loop: %s Failed\n' % number)
            continue
        print_s('Views %s/%s: %s' % (number, data_amount, view))
        write2xl(ROOT_PATH, workbook_name, (get_time(), view,))


# 获取一个up主的所有视频的信息
def get_videos_message(mid: str):
    # 获取个人空间的response
    space_response = SpiderCore.get_response(SPACE_DEFAULT_URL % (mid, PAGE_SIZE, 1))
    if space_response.status_code != 200:
        print_err('access mid: %s Failed\n' % mid)
        return
    author = re.findall(r'"name":"(.*?)"', SpiderCore.get_response(AUTHOR_DEFAULT_URL % mid).text, re.S)
    count = re.findall('"count":(.*?),', space_response.text, re.S)
    if author.__len__() <= 0 or count.__len__() <= 0:
        print_err('access mid: %s Failed\n' % mid)
        return
    author = author[0]
    count = int(count[-1])
    if count / PAGE_SIZE == int(count / PAGE_SIZE):
        page_count = int(count / PAGE_SIZE)
    else:
        page_count = int(count / PAGE_SIZE) + 1

    threads.video_serial = 0
    ScheduleThread(count).start()

    # 循环访问up主个人空间并处理
    thread_list = []
    for page_number in range(1, page_count + 1):
        thread_list.append(GetPageVideoThread(mid, PAGE_SIZE, page_number))
        thread_list[-1].start()
    for thread in thread_list:
        thread.join()
    print_s()
    time.sleep(5)  # 主动休息5秒防止风控

    author_workbook = openpyxl.Workbook()
    sheet = author_workbook.active
    sheet.title = 'Videos'
    sheet.append(('aid', 'title', 'view', 'danmaku', 'reply', 'favorite',
                  'coin', 'share', 'now_rank', 'his_rank', 'like'))
    for thread in thread_list:
        for result in thread.result:
            sheet.append(result)
    author_workbook.save('%s/%s_all_video.xlsx' % (ROOT_PATH, author))
    author_workbook.close()


def get_video(aid: str, page: int = None):
    if page is None:
        api_response = SpiderCore.get_response(API_DEFAULT_URL % aid)
        if api_response.status_code != 200:
            print_err('access video av%s Failed\n' % aid)
        api_json = api_response.json()
        pages = get_pages(api_json)
        if pages is not None:
            for page in range(1, len(pages) + 1):
                get_video(aid, page)
        return

    av_response = SpiderCore.get_response('%s?p=%d' % ((VIDEO_DEFAULT_URL % aid), page))
    if av_response.status_code != 200:
        print_err('access video av%s Failed\n' % aid)
        return
    print(av_response.url)
    playinfo_json = re.findall(r'<script>window.__playinfo__=(.*?)</script>', av_response.text, re.S)
    if playinfo_json.__len__() <= 0:
        print_err('Get playinfo from aid: %s Failed\n' % aid)
        return

    playinfo_json = json.loads(playinfo_json[0], encoding='utf-8')
    video_url, audio_url = handle_playinfo(playinfo_json)

    video_response = SpiderCore.get_response(video_url, stream=True)
    audio_response = SpiderCore.get_response(audio_url, stream=True)
    if video_response.status_code != 200 or audio_response.status_code != 200:
        print_err('Get video/audio failed\n')
        return

    video_file = open(temp_file_path('v%s' % aid), mode='wb')
    audio_file = open(temp_file_path('a%s' % aid), mode='wb')
    download(task_name='video', source_response=video_response, store_file=video_file)
    download(task_name='audio', source_response=audio_response, store_file=audio_file)
    video_file.close()
    audio_file.close()

    subprocess.run(FFMPEG_CMD % (video_file.name, audio_file.name, '%s_p%s.mp4' % (aid, page)))
    os.remove(video_file.name)
    os.remove(audio_file.name)
