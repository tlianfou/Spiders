# !/usr/bin/env python
# -*- coding:utf-8 -*-
from .settings import CONCURRENT_REQUESTS, \
    ROOT_PATH, DOWNLOAD_BLOCK_SIZE
from sys import stderr
import threading
import requests
import openpyxl
import tempfile
import hashlib
import shutil
import tqdm
import time
import os

requests_semaphore = threading.Semaphore(CONCURRENT_REQUESTS)
print_lock = threading.Lock()
serial_lock = threading.Lock()

TEMP_DIRECTORY = os.path.join(os.path.dirname(tempfile.NamedTemporaryFile().name), 'tmp_bilibiliSpider')
if os.path.exists(TEMP_DIRECTORY):
    shutil.rmtree(TEMP_DIRECTORY)
os.mkdir(TEMP_DIRECTORY)

FFMPEG_CMD = 'ffmpeg -i %s -i %s -c copy -map 0:v:0 -map 1:a:0 {}/%s'.format(ROOT_PATH)

MAIN_CID = '140213266'  # api访问码

HOME_URL = 'https://www.bilibili.com/'

SPACE_DEFAULT_URL = r'https://api.bilibili.com/x/space/arc/search?' \
                    r'mid=%s&ps=%d&tid=0&pn=%d&keyword=&order=pubdate&jsonp=jsonp'

AUTHOR_DEFAULT_URL = 'https://api.bilibili.com/x/space/acc/info?mid=%s&jsonp=jsonp'

VIDEO_DEFAULT_URL = 'https://www.bilibili.com/video/av%s'

API_DEFAULT_URL = 'https://api.bilibili.com/x/web-interface/view?aid=%s&cid={}'.format(MAIN_CID)

DANMAKU_DEFAULT_URL = 'https://api.bilibili.com/x/v1/dm/list.so?oid=%s'

VIP_URL = 'https://api.bilibili.com/x/vip/web/user/info?jsonp=jsonp'

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
    with print_lock:
        print(*args, end=end, sep=sep, file=file)


def print_err(s: str):
    with print_lock:
        stderr.write(s)


def get_time():
    return time.asctime()


def create_xl4views(local: str, name: str):
    path = '%s/%s' % (local, name)
    workbook = openpyxl.Workbook()
    workbook.active.title = 'View'
    workbook.active.append(('time', 'view'))
    workbook.save(path)
    workbook.close()


def write2xl(local: str, name: str, *args):
    path = '%s/%s' % (local, name)
    workbook = openpyxl.open(path)
    workbook.active.append(*args)
    workbook.save(path)
    workbook.close()


def download(task_name: str, source_response: requests.Response, store_file):
    length = int(source_response.headers['Content-Length'])
    with tqdm.tqdm(desc=task_name, total=length, unit='B',
                   ascii=True, unit_scale=True, unit_divisor=1024) as bar:
        for chunk in source_response.iter_content(chunk_size=DOWNLOAD_BLOCK_SIZE):
            store_file.write(chunk)
            bar.update(len(chunk))


def temp_file_path(name: str):
    return os.path.join(TEMP_DIRECTORY, name)


def get_title(api_json: dict):
    try:
        return api_json['data']['title']
    except:
        title_hash = hashlib.md5(str(api_json).encode('utf-8')).hexdigest()
        print_err('Get video title Failed, Used default title: %s\n' % title_hash)
        return title_hash


def get_pages(api_json: dict):
    try:
        return api_json['data']['pages']
    except:
        return None


def get_cover_url(api_json: dict):
    try:
        return api_json['data']['pic']
    except:
        return None


def get_view(api_json: dict):
    try:
        return api_json['data']['stat']['view']
    except:
        return None


def get_video_cid(api_json: dict):
    try:
        return api_json['data']['cid']
    except:
        return None


def handle_playinfo(playinfo_json: dict):
    try:
        video_block = playinfo_json['data']['dash']['video'][0]
        audio_block = playinfo_json['data']['dash']['audio'][0]

        # video_quality = video_block['id']
        # audio_quality = audio_block['id']
        video_url = video_block['baseUrl']
        audio_url = audio_block['baseUrl']

        return video_url, audio_url
    except:
        return None, None
