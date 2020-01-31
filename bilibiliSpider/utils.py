# !/usr/bin/env python
# -*- coding:utf-8 -*-

import openpyxl
import time


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
