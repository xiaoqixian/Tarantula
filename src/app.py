# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# > Author     : lunar
# > Email       : lunar_ubuntu@qq.com
# > Create Time: Sun 19 Jul 2020 04:03:14 PM CST

import logging; logging.basicConfig(level = logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web
from jinja2 import Environment, FileSystemLoader

from config import configs

import orm
from coroweb import add_routes, add_static
from models import User

@get('/')
def index(request):
    users = yield from User.findAll()
    return {
        '__templates__': 'index.html',
        'users': users
    }
