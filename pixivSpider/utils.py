# !/usr/bin/env python
# -*- coding:utf-8 -*-
import re
import requests


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
