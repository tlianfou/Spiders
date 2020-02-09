# !/usr/bin/env python
# -*- coding:utf-8 -*-

from .interface import get_illust
from .interface import get_illusts
from .interface import get_ranking
from .interface import search

# search 中保存文件存在误区
# imageSpider 的get_location和get_illust冲突
# searchSpider 传递file_name有误