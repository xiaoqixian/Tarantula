#python env:/bin/lib/python3.8
#!------------utf8------------
# > Author     : lunar
# > Mail       : lunar_ubuntu@qq.com
# > Create Time: Sat 18 Jul 2020 10:53:45 PM CST

import re, time, json, logging, hashlib, base64, asyncio

from coroweb import get, post

from models import User, Comment, Blog, next_id

@get('/')
def index(request):
    summary = "This is a summary test for index page"
    blogs = [
        Blog(id = '1', name = 'Test Blog', summary = summary, created_at = time.time() - 120),
        Blog(id = '2', name = 'Test Blog2', summary = summary, created_at = time.time() - 3600),
        Blog(id = '3', name = 'Test Blog3', summary = summary, created_at = time.time() - 7200)]
    return {
            '__template__': 'blog.html',
            'blogs': blogs
    }

@get('/api/users')
def api_get_users():
    users = yield from User.findAll(orderBy = 'created_at desc')
    for u in users:
        u.passwd = '******'
    return dict(users = users)

