# !/usr/bin/env python
# -*- coding:utf-8 -*-
from .settings import *
from .threads import *
from . import threads
import subprocess
import json
import sys
import re


# 获得封面图
def get_cover(aid: str):
    video_response = SpiderCore.get_response(VIDEO_DEFAULT_URL % aid)
    if video_response.status_code != 200:
        print_err('access video av%s Failed' % aid)
    video_title = re.findall(r'<title.*?>(.*?)</title>', video_response.text, re.S)
    if video_title.__len__() <= 0:
        sys.stderr.write('Get video title Failed: av%s, use default title: %s' % (aid, aid))
        video_title = aid
    else:
        video_title = video_title[0].split('_')[0].strip()

    cover_url = re.findall(r'"image" content="(.*?)">', video_response.text, re.S)
    if cover_url.__len__() <= 0:
        print_err('get cover form aid: %s Failed' % aid)
        return
    cover_url = cover_url[0]

    cover_response = SpiderCore.get_response(cover_url)
    if cover_response is None or cover_response.status_code != 200:
        print_err('access cover url: %s Failed!!!' % cover_url)
        return
    file_name = ('%s.%s' % (video_title, cover_url.split('/')[-1].split('.')[-1]))
    with open('%s/%s' % (ROOT_PATH, file_name), 'wb') as file:
        file.write(cover_response.content)


# 获得弹幕
def get_danmaku(aid: str):
    # 单个视频的response
    video_response = SpiderCore.get_response(API_DEFAULT_URL % (aid, MAIN_CID))
    if video_response.status_code != 200:
        print_err('access aid: %s Failed' % aid)
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
def get_views(aid: str, delay: int = 60, data_amount: int = 100):
    if data_amount < 1:
        print_err('Data amount must > 1')
        return

    # 单个视频response
    api_response = SpiderCore.get_response(API_DEFAULT_URL % (aid, MAIN_CID))
    if api_response.status_code != 200:
        print_err('Access aid: %s Failed' % aid)
        return

    title = re.findall(r'"title":"(.*?)"', api_response.text, re.S)
    if title.__len__() <= 0:
        print('Get video av%s title failed, use default title: default' % aid)
        title = 'default'
    else:
        title = title[0]
        print_s('The title of the video: %s' % title)

    print_s('Create workbook: %s/%s_views.xlsx to storing data' % (ROOT_PATH, title))
    workbook_name = '%s_views.xlsx' % title
    create_xl4views(ROOT_PATH, workbook_name)
    print_s('Complete...Begin to pull views...')

    # 提前获取和输出第一次获取的数据
    view = re.findall(r'"view":(.*?),', api_response.text, re.S)[0]
    write2xl(ROOT_PATH, workbook_name, (get_time(), int(view),))
    print_s('Views %s/%s: %s' % (1, data_amount, view))
    # 循环获取播放量
    for number in range(2, data_amount + 1):
        time.sleep(delay)
        api_response = SpiderCore.get_response(API_DEFAULT_URL % (aid, MAIN_CID))
        if api_response.status_code != 200:
            print_err('access number: %s Failed' % number)
            continue
        view = re.findall(r'"view":(.*?),', api_response.text, re.S)
        if view.__len__() <= 0:
            print_err('failed to get view at number: %s' % number)
            continue
        print_s('Views %s/%s: %s' % (number, data_amount, view[0]))
        write2xl(ROOT_PATH, workbook_name, (get_time(), int(view[0]),))


# 获取一个up主的所有视频
def get_videos_message(mid: str):
    # 获取个人空间的response
    space_response = SpiderCore.get_response(SPACE_DEFAULT_URL % (mid, PAGE_SIZE, 1))
    if space_response.status_code != 200:
        print_err('access mid: %s Failed' % mid)
        return
    author = re.findall(r'"name":"(.*?)"', SpiderCore.get_response(AUTHOR_DEFAULT_URL % mid).text, re.S)
    count = re.findall('"count":(.*?),', space_response.text, re.S)
    if author.__len__() <= 0 or count.__len__() <= 0:
        print_err('access mid: %s Failed' % mid)
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


def get_video(aid: str):
    av_response = SpiderCore.get_response(VIDEO_DEFAULT_URL % aid)
    if av_response.status_code != 200:
        print_err('access video av%s Failed' % aid)
        return

    playinfo_json = re.findall(r'<script>window.__playinfo__=(.*?)</script>', av_response.text, re.S)
    try:
        playinfo_json = json.loads(playinfo_json[0], encoding='utf-8')
        video_block = playinfo_json['data']['dash']['video'][0]
        audio_block = playinfo_json['data']['dash']['audio'][0]

        # video_quality = video_block['id']
        # audio_quality = audio_block['id']
        video_url = video_block['baseUrl']
        audio_url = audio_block['baseUrl']
    except TypeError or IndexError or KeyError:
        print_err('get ajax Failed in video: av%s' % aid)
        return

    video_response = SpiderCore.get_response(video_url, stream=True)
    audio_response = SpiderCore.get_response(audio_url, stream=True)
    if video_response.status_code != 200 or audio_response.status_code != 200:
        print_err('Get video/audio failed')
        return

    video_file = open(temp_file_path('v%s' % aid), mode='wb')
    audio_file = open(temp_file_path('a%s' % aid), mode='wb')
    download('video', video_response, video_file)
    download('audio', audio_response, audio_file)
    video_file.close()
    audio_file.close()

    subprocess.run(FFMPEG_CMD % (video_file.name, audio_file.name, '%s.mp4' % aid))
    os.remove(video_file.name)
    os.remove(audio_file.name)
