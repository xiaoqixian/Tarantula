# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# > Author     : lunar
# > Email       : lunar_ubuntu@qq.com
# > Create Time: Tue 21 Jul 2020 11:10:11 PM CST

# 接下来需要实现一个web框架，

# inspect库可以用于查看函数的属性
# functools库用于在制作装饰器时保存函数的元数据
import asyncio, inspect, functools


# 首先实现两个装饰器:get和post
# 这两个装饰器用于为函数装饰一点__method__和__route__的属性
# 由于是带参数的装饰器，所以需要定义三层函数
def get(path):
    # define a decorator @get('/path')
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator

def post(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator

# 这两个装饰器在所有的handler中几乎都要用到

# 封装一个请求处理类，但是只有一个__init__和__call__方法
# 众所周知，__call__可以使得类实例像函数一样调用。所以这实际就是好用一点的
# 函数而已。

# python http request介绍
# request属性：
# 1. path:表示提交请求页面完整地址的字符串，不包括域名，如"/music/bands/the_beatles/"。
# 2. method:表示提交请求使用的HTTP方法。(GET、POST)
# 3. GET:一个类字典对象，包含所有的HTTP的GET参数的信息。
# 4. POST:一个类字典对象，包含所有的HTTP的POST参数的信息。注意： POST 并不 包含文件上传信息。
# 5. REQUEST:为了方便而创建，这是一个类字典对象，先搜索 POST ，再搜索 GET 。强烈建议使用 GET 和 POST，而不是 REQUEST 。
# 6. COOKIES:一个标准的Python字典，包含所有cookie。键和值都是字符串。
# 7. FILES:一个类字典对象，包含所有上传的文件。 FILES 的键来自 <input type="file" name="" /> 中的 name。 FILES 的值是一个标准的Python字典，包含以下三个键： filename ：字符串，表示上传文件的文件名。content-type ：上传文件的内容类型。content ：上传文件的原始内容。注意 FILES 只在请求的方法是 POST，并且提交的 <form> 包含enctype="multipart/form-data"时才包含数据。否则， FILES 只是一个空的类字典对象。
class RequestHandler:

    def __init__(self, app, func):
        self.app = app
        self.func = func


    async def __call__(self,request):
        # 接下来考虑一个request应该如何处理

