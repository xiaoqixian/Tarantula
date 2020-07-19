# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# > Author     : lunar
# > Email       : lunar_ubuntu@qq.com
# > Create Time: Sun 19 Jul 2020 04:38:31 PM CST

import config_default

class Dict(dict):
    # 实现一个支持x.y格式的字典
    def __init__(self, names = (), values = (), **kw):
        super(Dict, self).__init__(**kw)
        for k,v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

        def __setattr__(self, key, value):
            self[key] = value

def merge(defauts, override):
    r =
    for k,v in defaults.items():

